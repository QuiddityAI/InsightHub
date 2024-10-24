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
