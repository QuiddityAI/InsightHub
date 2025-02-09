import datetime
import hashlib
import logging
import os
import tarfile
import uuid
import zipfile

from django.core.files import File
from werkzeug.utils import secure_filename

from data_map_backend.models import ServiceUsage
from ingest.logic.common import UPLOADED_FILES_FOLDER
from ingest.schemas import UploadedFileMetadata, UploadedOrExtractedFile

# only applies to single files, not archives
# (this is also why it can't be enforced by flask's max_content_length)
MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def store_uploaded_file(file: File, dataset_id: int) -> tuple[str, str]:
    temp_path = f"{UPLOADED_FILES_FOLDER}/temp_{uuid.uuid4()}"

    with open(temp_path, "wb") as f:
        f.write(file.read())
    # check if file size is within limits, otherwise delete it to prevent filling up the disk
    # (file size can't be determined earlier as it might be a stream)
    file_size = os.path.getsize(temp_path)
    if file_size > MAX_SINGLE_FILE_SIZE:
        os.remove(temp_path)
        raise ValueError(
            f"File size of {file_size / 1024 / 1024:.2f} MB exceeds the limit of {MAX_SINGLE_FILE_SIZE / 1024 / 1024:.2f} MB"
        )
    sub_path, md5 = _move_to_path_containing_md5(temp_path, file.name or "", dataset_id)
    return sub_path, md5


def unpack_archive(file: File, dataset_id: int, user_id: int) -> tuple[list[UploadedOrExtractedFile], list[str]]:
    assert file.name
    failed_files = []
    extracted_files: list[UploadedOrExtractedFile] = []
    logging.warning(f"extracting archive file: {file.name}")
    is_tar = file.name.endswith(".tar.gz")
    tempfile = f"{UPLOADED_FILES_FOLDER}/temp_{uuid.uuid4()}" + (".tar.gz" if is_tar else f".zip")
    with open(tempfile, "wb") as f:
        f.write(file.read())

    usage_tracker = ServiceUsage.get_usage_tracker(user_id, "upload_items")
    remaining_allowed_items = usage_tracker.limit_per_period - usage_tracker.get_current_period().usage

    try:
        if is_tar:
            archive = tarfile.open(tempfile, "r:gz")
            members = archive.getmembers()
        else:
            archive = zipfile.ZipFile(tempfile)
            members = archive.infolist()
        logging.warning(f"contains {len(members)} files")

        # check if user is allowed to upload this many files before storing them
        # to prevent filling up the disk with files that can't be imported
        if len(members) > remaining_allowed_items:
            raise ValueError(f"Too many files in archive, limit is {remaining_allowed_items}")

        for member in members:
            file_size = member.size if isinstance(member, tarfile.TarInfo) else member.file_size
            # check if file size is within limits before extracting
            if file_size > MAX_SINGLE_FILE_SIZE:
                raise ValueError(
                    f"File size of {file_size / 1024 / 1024:.2f} MB exceeds the limit of {MAX_SINGLE_FILE_SIZE / 1024 / 1024:.2f} MB"
                )
            full_path = member.name if isinstance(member, tarfile.TarInfo) else member.filename
            file_name = os.path.basename(full_path)
            if file_name == ".DS_Store":
                continue
            folder = os.path.dirname(full_path)
            logging.warning(f"extracting file: {full_path}")
            try:
                sub_path, md5 = _store_compressed_file(archive, member, dataset_id)
            except Exception as e:
                logging.warning(f"failed to extract file: {e}")
                failed_files.append({"filename": file.name + " -> " + full_path, "reason": str(e)})
                continue
            if not sub_path:
                continue
            updated_at_iso = None
            if isinstance(member, tarfile.TarInfo):
                updated_at_sec_since_epoch = member.mtime
                updated_at_iso = datetime.datetime.fromtimestamp(updated_at_sec_since_epoch).isoformat()
            if isinstance(member, zipfile.ZipInfo):
                updated_at_tuple = member.date_time  # year, month, day, hour, min, sec
                updated_at_iso = datetime.datetime(*updated_at_tuple).isoformat()
            extracted_files.append(
                UploadedOrExtractedFile(
                    local_path=sub_path,
                    original_filename=file_name,
                    metadata=UploadedFileMetadata(
                        updated_at=updated_at_iso, size_in_bytes=file_size, folder=folder, md5_hex=md5
                    ),
                )
            )
    except Exception as e:
        logging.warning(f"failed to extract archive file: {e}")
        # print stacktrace
        import traceback

        traceback.print_exc()
        failed_files.append({"filename": file.name, "reason": str(e)})
    finally:
        os.remove(tempfile)
    return extracted_files, failed_files


def _store_compressed_file(
    archive: tarfile.TarFile | zipfile.ZipFile, member: tarfile.TarInfo | zipfile.ZipInfo, dataset_id: int
) -> tuple[str, str] | tuple[None, None]:
    if isinstance(member, tarfile.TarInfo) and not member.isfile():
        return None, None
    if isinstance(member, zipfile.ZipInfo) and member.is_dir():
        return None, None
    filename = member.name if isinstance(member, tarfile.TarInfo) else member.filename
    if "MACOSX_" in filename or "_MACOSX" in filename:
        return None, None
    if isinstance(archive, tarfile.TarFile) and isinstance(member, tarfile.TarInfo):
        file = archive.extractfile(member)
    else:
        assert isinstance(archive, zipfile.ZipFile) and isinstance(member, zipfile.ZipInfo)
        file = archive.open(member)
    if file is None:
        logging.warning(f"failed to extract file: {filename}")
        raise ValueError("failed to extract file")
    temp_path = f"{UPLOADED_FILES_FOLDER}/temp_{uuid.uuid4()}"
    with file:
        with open(temp_path, "wb") as f:
            f.write(file.read())
    sub_path, md5 = _move_to_path_containing_md5(temp_path, filename, dataset_id)
    return sub_path, md5


def _move_to_path_containing_md5(temp_path: str, filename: str, dataset_id: int):
    md5 = hashlib.md5(open(temp_path, "rb").read()).hexdigest()
    secure_name = secure_filename(filename)
    suffix = secure_name.split(".")[-1]
    filename = secure_name[: -(len(suffix) + 1)] + f"_{md5}.{suffix}"
    sub_folder = f"{dataset_id}/{md5[:2]}"
    if not os.path.exists(f"{UPLOADED_FILES_FOLDER}/{sub_folder}"):
        os.makedirs(f"{UPLOADED_FILES_FOLDER}/{sub_folder}")
    sub_path = f"{sub_folder}/{filename}"
    path = f"{UPLOADED_FILES_FOLDER}/{sub_path}"
    os.rename(temp_path, path)
    return sub_path, md5
