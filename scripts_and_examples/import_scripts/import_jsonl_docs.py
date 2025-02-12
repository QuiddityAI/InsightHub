import json
import os
import tempfile

from data_backend_client import upload_files

batch = []
batch_size = 5

for l in open("scripts_and_examples/generated_data/2025-01-18/docs.jsonl").readlines():
    doc = json.loads(l)
    with tempfile.NamedTemporaryFile(prefix=doc["id"] + "_", delete=False, mode="w", suffix=".txt") as temp_file:
        json.dump(doc["doc"], temp_file)
        batch.append(temp_file.name)

    if len(batch) >= batch_size:
        upload_files(
            dataset_id=113,
            schema_identifier="filesystem_file_english",
            user_id=1,
            organization_id=11,
            import_converter="office_document",
            file_paths=batch,
            exclude_prefix=None,
            skip_generators=False,
        )
        for f in batch:
            os.remove(f)
        batch = []

if batch:
    upload_files(
        dataset_id=113,
        schema_identifier="filesystem_file_english",
        user_id=1,
        organization_id=11,
        import_converter="office_documents",
        file_paths=batch,
        exclude_prefix=None,
        skip_generators=False,
    )
    for f in batch:
        os.remove(f)
    batch = []
