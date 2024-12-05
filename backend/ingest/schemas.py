from typing import Optional
from ninja import Schema
from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile


class UploadedFileMetadata(Schema):
    folder: Optional[str] = None
    created_at: Optional[str] = None  # isoformat
    updated_at: Optional[str] = None  # isoformat
    size_in_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    md5_hex: Optional[str] = None


class CustomUploadedFile(Schema):
    """ File (could be an archive) coming from form or API, with some extra metadata """
    uploaded_file: DjangoUploadedFile
    metadata: Optional[UploadedFileMetadata] = None

    class Config:
        arbitrary_types_allowed = True


class UploadedOrExtractedFile(Schema):
    """ Either an uploaded file, or a file extracted from an uploaded archive, already stored on disk """
    local_path: str  # relative to UPLOADED_FILES_FOLDER
    original_filename: str
    metadata: Optional[UploadedFileMetadata] = None


class AiMetadataResult(Schema):
    title: str = ""
    document_type: str = ""
    summary: str = ""
    tags: list[str] = []
    date: Optional[str] = None  # isoformat
    time: Optional[str] = None  # isoformat
    document_language: str = ""  # two letter code


class AiFileProcessingInput(Schema):
    file_name: str = ""
    folder: str | None = None
    uploaded_file_path: str = ""
    file_created_at: Optional[str] = None  # isoformat
    file_updated_at: Optional[str] = None  # isoformat


class AiFileProcessingOutput(Schema):
    content_date: Optional[str] = None  # isoformat
    content_time: Optional[str] = None  # isoformat
    description: str = ""
    document_language: str = ""  # two letter code
    full_text: str = ""
    full_text_chunks: list[dict] = []
    summary: str = ""
    thumbnail_path: str | None = None
    title: str = ""
    type_description: str = ""
    people: list[str] = []
