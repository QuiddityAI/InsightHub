import logging
import json

from django.http import HttpResponse
from django.utils.datastructures import MultiValueDict
from ninja import NinjaAPI, Form, File, UploadedFile

from data_map_backend.views.other_views import get_or_create_default_dataset

from ingest.schemas import CustomUploadedFile, UploadedFileMetadata
from ingest.logic.upload_files import upload_files_or_forms

api = NinjaAPI(urls_namespace="ingest")


@api.post("upload_files")
def upload_files_route(
    request,
    dataset_id: Form[int],
    schema_identifier: Form[str],
    user_id: Form[int],
    organization_id: Form[int],
    import_converter: Form[str],
    collection_id: Form[int | None] = None,
    collection_class: Form[str | None] = None,
    dataset_auth_token: Form[str | None] = None,
    blocking: Form[bool] = False,
    *args,
    **kwargs,
):
    """ Upload individual files or zip archives.
    Will be stored, extracted and post-processed (OCR etc.), then imported. """
    if not request.user.is_authenticated and dataset_auth_token != "fixme":  # TODO: use proper auth token
        return HttpResponse(status=401)

    if dataset_id == -1:
        result = get_or_create_default_dataset(user_id, schema_identifier, organization_id)
        if isinstance(result, HttpResponse):
            return result
        dataset = result
        dataset_id = dataset.id  # type: ignore

    FILES: MultiValueDict = request.FILES
    custom_uploaded_files = []
    for key, file in FILES.items():
        custom_file = CustomUploadedFile(uploaded_file=file)
        metadata = request.POST.get(f"{key}_metadata")
        if metadata:
            logging.warning(f"Metadata for file {key}: {metadata}")
            custom_file.metadata = UploadedFileMetadata(**json.loads(metadata))
        custom_uploaded_files.append(custom_file)
    task_id = upload_files_or_forms(dataset_id, import_converter, custom_uploaded_files, None, collection_id, collection_class, user_id, blocking)
    # usually, all in-memory files of the request would be closed and deleted after the request is done
    # in this case, we want to keep them open and close them manually in the background thread
    # so we need to remove the files from the request object:
    # (this was ported from flask to Django, not sure if it's necessary in Django)
    FILES.clear()
    return {"task_id": task_id, "dataset_id": dataset_id}
