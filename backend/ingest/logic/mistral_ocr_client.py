#!/usr/bin/env python
# coding: utf-8

"""
Mistral OCR Client for PDF processing and metadata extraction.
"""

import base64
import io
import logging
import re
import time
import traceback as tb
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple, Union
import concurrent.futures


# Configure logging for detailed output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mistral_ocr_client")

import dspy
from mistralai import Mistral
from mistralai.models import OCRResponse
from pdf2image import convert_from_path
from pydantic import BaseModel, Field

from backend.config.llm import default_mistral_ocr_models
from backend.data_map_backend.utils import DotDict


class ChunkType(str, Enum):
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"
    VISUAL_PAGE = "visual_page"
    OTHER = "other"


class PDFError(BaseModel):
    exc: str = ""
    traceback: Union[str, List[str]] = ""
    file: str = ""


class PDFChunk(BaseModel):
    page: Optional[int] = None
    coordinates: Optional[List[Tuple[float, float]]] = None
    section: str = ""
    prefix: str = ""
    non_embeddable_content: str = ""
    text: str = ""
    suffix: str = ""
    locked: bool = False
    chunk_type: ChunkType = ChunkType.TEXT


class FileFeatures(BaseModel):
    filename: str = ""
    file: Optional[str] = None
    is_scanned: Optional[bool] = None


class MetaInfo(BaseModel):
    doi: str = ""
    title: str = ""
    document_type: str = ""
    abstract: str = ""
    authors: List[str] = Field(default_factory=list)
    pub_date: str = ""
    mentioned_date: str = ""
    language: str = ""
    detected_language: str = ""
    file_features: Optional[FileFeatures] = None
    npages: Optional[int] = None
    thumbnail: Optional[Union[bytes, str]] = None
    extra_metainfo: dict = Field(default_factory=dict)
    ai_metadata: str = ""
    search_description: str = ""


class PDFDoc(BaseModel):
    metainfo: MetaInfo = Field(default_factory=MetaInfo)
    chunks: List[PDFChunk] = Field(default_factory=list)
    full_text: str = ""


# Utility functions
def encode_pdf(pdf_path: str) -> Optional[str]:
    """Encode the PDF to base64 string. Returns None on error."""
    logger.debug(f"Encoding PDF: {pdf_path}")
    try:
        with open(pdf_path, "rb") as pdf_file:
            logger.info(f"Successfully opened PDF: {pdf_path}")
            return base64.b64encode(pdf_file.read()).decode("utf-8")
    except FileNotFoundError:
        logger.error(f"Error: The file {pdf_path} was not found.")
        return None
    except Exception as e:
        logger.error(f"Error encoding PDF {pdf_path}: {e}")
        return None


def get_combined_markdown(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text and images

    Returns:
        Combined markdown string with embedded images
    """
    markdowns: List[str] = []
    logger.debug("Combining OCR response pages into markdown.")
    for page in ocr_response.pages:
        # Build image map if images exist on the page (kept for potential use)
        image_data: dict = {img.id: img.image_base64 for img in getattr(page, "images", [])}
        # Use the page markdown provided by the OCR response
        markdowns.append(getattr(page, "markdown", ""))
    return "\n\n".join(markdowns)


def remove_images_from_markdown(markdown: str) -> str:
    """Remove image links (e.g., ![alt](url)) from markdown text."""
    logger.debug("Removing images from markdown.")
    return re.sub(r"!\[.*?\]\(.*?\)", "", markdown)


def combine_short_sections(
    sections: List[dict],
    min_len: int = 100,
    max_len: int = 384,
    text_key: str = "text",
) -> List[dict]:
    """
    Combine consecutive sections if their length is below min_len (in words),
    but only if their combined length does not exceed max_len (in words).
    """

    logger.debug(f"Combining short sections: {len(sections)} sections, min_len={min_len}, max_len={max_len}")

    def word_count(text: str) -> int:
        return len(text.split())

    combined: List[dict] = []
    buffer: Optional[dict] = None

    for section in sections:
        text = section[text_key]
        if buffer is None:
            buffer = section.copy()
            continue

        buffer_len = word_count(buffer[text_key])
        text_len = word_count(text)
        if (buffer_len < min_len or text_len < min_len) and (buffer_len + text_len <= max_len):
            buffer[text_key] = buffer[text_key].rstrip() + "\n" + text.lstrip()
            buffer["section"] += " | " + section.get("section", "")
            continue

        combined.append(buffer)
        buffer = section.copy()

    if buffer is not None:
        combined.append(buffer)

    return combined


def chunk_markdown_sections(markdown: str, max_tokens: int = 384) -> List[PDFChunk]:
    """
    Chunk a markdown research article into sections and further split large sections.
    """
    logger.debug(f"Chunking markdown into sections with max_tokens={max_tokens}")
    tokenizer = lambda s: s.split()

    # Regex to find section headers (e.g., ## Section, ### Subsection)
    section_pattern = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)
    matches = list(section_pattern.finditer(markdown))

    if not matches:
        logger.info("No section headers found in markdown. Splitting as a single section.")
        chunks_dict = _split_text_to_chunks(markdown, "Document", max_tokens, tokenizer)
        return [PDFChunk(section=c["section"], text=c["text"], chunk_type=ChunkType.TEXT) for c in chunks_dict]

    chunks: List[dict] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        section_title = match.group(2).strip()
        section_text = markdown[start:end].strip()
        logger.debug(f"Splitting section: {section_title}")
        section_chunks = _split_text_to_chunks(section_text, section_title, max_tokens, tokenizer)
        chunks.extend(section_chunks)

    # Prepend the section header to each chunk's text
    chunks = [ch | {"text": f"## {ch['section']}\n\n{ch['text']}"} for ch in chunks if ch["text"].strip()]

    # Combine very short sections
    chunks = combine_short_sections(chunks, min_len=100, max_len=max_tokens, text_key="text")

    pdf_chunks: List[PDFChunk] = [
        PDFChunk(section=section["section"], text=section["text"], chunk_type=ChunkType.TEXT) for section in chunks
    ]

    logger.info(f"Total chunks created: {len(pdf_chunks)}")
    return pdf_chunks


def _split_text_to_chunks(text: str, section_title: str, max_tokens: int, tokenizer) -> List[dict]:
    tokens = tokenizer(text)
    n_tokens = len(tokens)
    logger.debug(f"Splitting section '{section_title}' into chunks. Total tokens: {n_tokens}")
    if n_tokens <= max_tokens:
        return [{"section": section_title, "text": text, "chunk_idx": 0}]

    n_chunks = (n_tokens + max_tokens - 1) // max_tokens
    chunk_size = n_tokens // n_chunks
    chunks: List[dict] = []
    for i in range(n_chunks):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < n_chunks - 1 else n_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = " ".join(chunk_tokens)
        chunks.append({"section": section_title, "text": chunk_text, "chunk_idx": i})
    logger.debug(f"Section '{section_title}' split into {len(chunks)} chunks.")
    return chunks


# DSPy signatures for metadata extraction
class MetainfoSignature(dspy.Signature):
    """Given the text of a research article, extract its metadata. If not available, return N/A.
    Don't use quotation marks in the output.
    """

    fulltext: str = dspy.InputField(description="The full text of the research article in markdown format.")
    authors: List[str] = dspy.OutputField(description="List of authors of the research article.")
    title: str = dspy.OutputField(description="The title of the research article.")
    pub_date: str = dspy.OutputField(description="The publication date of the research article.")
    doi: str = dspy.OutputField(description="The DOI of the research article.")
    document_type: str = dspy.OutputField(
        description="The type of the document (e.g., journal article, conference paper). No more than 3 words"
    )


class AbstractSignature(dspy.Signature):
    """Given the text of a research article, extract its abstract. If abstract is not available, return N/A"""

    fulltext: str = dspy.InputField(description="The full text of the research article in markdown format.")
    abstract: str = dspy.OutputField(description="The abstract of the research article.")


class SummarySignature(dspy.Signature):
    """Given the text of a research article, extract its summary. The summary must follow the rules for the abstract.
    The summary should be concise and capture the main findings of the research article. Do not exceed 6-7 sentences.
    """

    fulltext: str = dspy.InputField(description="The full text of the research article in markdown format.")
    summary: str = dspy.OutputField(description="The summary of the research article.")


class LanguageSignature(dspy.Signature):
    """Given the text of an article, detect its language."""

    fulltext: str = dspy.InputField(description="The full text of the research article in markdown format.")
    detected_language: str = dspy.OutputField(
        description="The detected language of the research article as two-letter code, e.g. en, de, or jp"
    )

class SearchDescriptionSignature(dspy.Signature):
    """Given the information about article, extract a short description used for search indexing.
    The description should be concise and capture the main summary of the research article.
    Limit the length of description to a single sentence."""

    article_info: str = dspy.InputField(description="The information about the article.")
    search_description: str = dspy.OutputField(
        description="A short search description of the research article, no more than 100 characters."
    )


class TranslateSignature(dspy.Signature):
    """Given the text, translate it to English, keep the original formatting."""

    text: str = dspy.InputField(description="The text in markdown format.")
    translated_text: str = dspy.OutputField(description="The translated text in English.")


class Translator(dspy.Module):
    """A module that translates text to English."""

    def __init__(self):
        self.pred = dspy.Predict(TranslateSignature)

    def _cut_managable_sections(self, markdown: str, max_tokens: int = 1024) -> List[str]:
        tokenizer = lambda s: s.split()

        # Split markdown by section headers (e.g., ##, ###, etc.) and keep pieces
        section_pattern = re.compile(r"^(#{1,6})\\s+.+", re.MULTILINE)
        splits = [m.start() for m in section_pattern.finditer(markdown)]
        splits.append(len(markdown))

        sections: List[str] = []
        prev = 0
        for s in splits:
            if prev < s:
                sections.append(markdown[prev:s].strip())
            prev = s
        sections = [s for s in sections if s]

        # Recombine sections if they're too short
        combined_sections: List[str] = []
        buffer = ""
        tokenizer = lambda s: s.split()
        for section in sections:
            if not buffer:
                buffer = section
            else:
                if len(tokenizer(buffer)) + len(tokenizer(section)) < max_tokens:
                    buffer = buffer + "\\n\\n" + section
                else:
                    combined_sections.append(buffer)
                    buffer = section
        if buffer:
            combined_sections.append(buffer)
        logger.debug(f"Cut markdown into {len(combined_sections)} manageable sections for translation.")
        return combined_sections

    def forward(self, markdown: str) -> str:
        logger.info("Translating markdown to English if needed.")
        sections = self._cut_managable_sections(markdown)
        translated_sections: List[str] = []
        for section in sections:
            translated = self.pred(text=section)
            translated_sections.append(translated.translated_text)
        return "\\n\\n".join(translated_sections)


def prepare_markdown(markdown: str) -> str:
    """Prepare markdown for processing by removing images and translating if needed."""
    logger.info("Preparing markdown for further processing.")
    markdown = remove_images_from_markdown(markdown)
    pred_language = dspy.Predict(LanguageSignature)
    lang = pred_language(fulltext=markdown[:5000]).detected_language
    logger.info(f"Detected language: {lang}")
    if lang != "en":
        translator = Translator()
        logger.info("Translating markdown to English.")
        markdown = translator(markdown)
    return markdown


def extract_metainfo_llm(markdown: str) -> MetaInfo:
    """Extract metadata from markdown text using DSPy signatures."""
    logger.info("Extracting metadata from markdown using LLM.")
    pred_metainfo = dspy.Predict(MetainfoSignature)
    pred_abstract = dspy.Predict(AbstractSignature)
    pred_summary = dspy.Predict(SummarySignature)
    pred_search_description = dspy.Predict(SearchDescriptionSignature)

    metainfo = pred_metainfo(fulltext=markdown[:5000])
    abstract = pred_abstract(fulltext=markdown[:5000]).abstract
    if not abstract or len(abstract) < 20:
        logger.info("Abstract is too short or not provided, generating summary instead.")
        abstract = pred_summary(fulltext=markdown).summary

    info = f"Title: {metainfo.title}\n Abstract: {abstract}\n"
    search_description = pred_search_description(article_info=info).search_description

    return MetaInfo(
        abstract=abstract,
        title=metainfo.title if metainfo.title != "N/A" else "",
        authors=metainfo.authors if metainfo.authors != "N/A" and metainfo.authors is not None else [],
        pub_date=metainfo.pub_date if metainfo.pub_date != "N/A" else "",
        doi=metainfo.doi if metainfo.doi != "N/A" else "",
        document_type=metainfo.document_type if metainfo.document_type != "N/A" else "",
        detected_language="en",
        search_description=search_description,
    )


def convert_pdf_to_jpg(file: str) -> bytes:
    """Convert first page of PDF to JPEG bytes."""
    logger.info(f"Converting PDF to JPEG thumbnail: {file}")
    # pdf2image pages are 1-indexed; request the first page explicitly
    pages_as_pil = convert_from_path(file, first_page=1, last_page=1, dpi=100)
    pil_page = pages_as_pil[0]
    buff = io.BytesIO()
    pil_page.save(buff, "JPEG")
    raw_bytes = buff.getvalue()
    buff.close()
    for p in pages_as_pil:
        p.close()
    return raw_bytes


def _extract_using_mistral_single(file_path: str) -> PDFDoc:
    logger.info(f"Processing file with Mistral OCR: {file_path}")
    client = Mistral(api_key=default_mistral_ocr_models.api_key)

    base64_pdf = encode_pdf(file_path)
    if not base64_pdf:
        logger.error(f"Could not read PDF: {file_path}")
        raise FileNotFoundError(f"Could not read PDF: {file_path}")

    # Call the OCR API
    logger.info(f"Calling Mistral OCR API for file: {file_path}")
    pdf_response = client.ocr.process(
        model=default_mistral_ocr_models.ocr,
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{base64_pdf}",
        },
        include_image_base64=False,
        pages = list(range(50)) # Process up to first 50 pages
    )
    logger.info(f"OCR API call complete for file: {file_path}")
    lm = dspy.LM(**default_mistral_ocr_models.metadata_llm_kwargs)

    with dspy.context(lm=lm):
        logger.info(f"Extracting markdown and metadata for file: {file_path}")
        # get combined markdown from OCR response
        raw_markdown = get_combined_markdown(pdf_response)
        # remove images and translate if necessary
        markdown = prepare_markdown(raw_markdown)
        chunks = chunk_markdown_sections(markdown)
        metainfo = extract_metainfo_llm(markdown)

    metainfo.npages = len(getattr(pdf_response, "pages", []))
    metainfo.thumbnail = convert_pdf_to_jpg(file_path)
    metainfo.file_features = FileFeatures(filename=file_path)
    metainfo.language = metainfo.detected_language

    final_pdfdoc = PDFDoc(metainfo=metainfo, chunks=chunks, full_text=markdown)
    logger.info(f"Finished processing file: {file_path}")
    return final_pdfdoc


def process_files_with_retries(
    file_paths: List[str],
    process_func: Callable[[str], Any],
    max_threads: int = 5,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    task_timeout: float = 120.0,
) -> Tuple[List[Any], List[PDFError]]:
    """
    Process a list of files in parallel using threads, retrying failed files up to max_retries times.
    Returns a tuple: (list of successful results, list of PDFError objects for failed files)
    """
    logger.info(f"Starting parallel processing of {len(file_paths)} files with up to {max_threads} threads.")
    results_map: dict[str, Any] = {fp: None for fp in file_paths}
    failed = []
    attempts = {fp: 0 for fp in file_paths}
    remaining = set(file_paths)

    while remaining:
        logger.info(f"Files remaining to process: {len(remaining)}")
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_to_file = {executor.submit(process_func, fp): fp for fp in remaining}
            next_remaining = set()
            for future in as_completed(future_to_file):
                fp = future_to_file[future]
                try:
                    logger.info(f"Processing file: {fp}")
                    result = future.result(timeout=task_timeout)
                    logger.info(f"Successfully processed file: {fp}")
                    results_map[fp] = result
                except Exception as e:
                    # Check for timeout
                    is_timeout = False
                    try:
                        if isinstance(e, concurrent.futures.TimeoutError):
                            is_timeout = True
                    except ImportError:
                        pass
                    attempts[fp] += 1
                    if attempts[fp] <= max_retries:
                        logger.warning(f"Retrying file {fp} (attempt {attempts[fp]}/{max_retries}) due to error: {e}")
                        next_remaining.add(fp)
                    else:
                        err_msg = f"Timeout after {task_timeout}s: {str(e)}" if is_timeout else str(e)
                        logger.error(f"Failed to process file {fp} after {max_retries} attempts: {err_msg}")
                        err = PDFError(exc=err_msg, traceback=tb.format_exception(type(e), e, e.__traceback__), file=fp)
                        failed.append(err)
                        dummy_doc = PDFDoc(
                            metainfo=MetaInfo(title="__failed__", file_features=FileFeatures(filename=fp)), chunks=[], full_text=""
                        )
                        results_map[fp] = dummy_doc
            remaining = next_remaining
        if remaining:
            logger.info(f"Sleeping for {retry_delay} seconds before retrying failed files.")
            time.sleep(retry_delay)
    # Maintain the order of file_paths in the results
    results = [results_map[fp] for fp in file_paths]
    logger.info(f"Processing complete. {len(failed)} files failed.")
    return results, failed


def extract_using_mistral(
    file_paths: list[str],
    max_threads: int = 5,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> tuple[list[DotDict], list[DotDict]]:
    """
    Process a list of PDF files using the Mistral OCR client, with retries and parallelism.
    Returns a tuple: (list of successful PDFDoc results, list of PDFError objects for failed files)
    """
    logger.info(f"Starting extract_using_mistral for {len(file_paths)} files.")
    results: list[PDFDoc]
    failed: list[PDFError] = []
    results, failed = process_files_with_retries(
        file_paths=file_paths,
        process_func=_extract_using_mistral_single,
        max_threads=max_threads,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    # Ensure failed is a list of PDFError objects
    failed_errors: list[PDFError] = []
    for err in failed:
        if isinstance(err, PDFError):
            failed_errors.append(err)
        elif isinstance(err, str):
            failed_errors.append(PDFError(exc=err, file=""))
        else:
            # fallback for unknown error type
            failed_errors.append(PDFError(exc=str(err), file=""))

    docs = [DotDict(doc.model_dump()) for doc in results]
    errors = [DotDict(err.model_dump()) for err in failed_errors]

    if errors:
        logger.error(f"Failed to process {len(errors)} files: {errors}")
        for error in errors:
            logger.error(f"Error processing file {error.file}: {error.exc}\n{error.traceback}")

    logger.info(f"extract_using_mistral complete. {len(docs)} docs, {len(errors)} errors.")
    return docs, errors
