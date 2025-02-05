import json
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models.errors import SDKError

s = UnstructuredClient(
    server_url="http://localhost:8000",
    api_key_auth="visual_data_map",
)

filename = "_sample_docs/layout-parser-paper-fast.pdf"

with open(filename, "rb") as f:
    # Note that this currently only supports a single file
    files = shared.Files(
        content=f.read(),
        file_name=filename,
    )

req = shared.PartitionParameters(
    files=files,
    # Other partition params
    strategy="ocr_only",
    languages=["eng"],
)

try:
    resp = s.general.partition(req)
    # print(resp.elements[0])
except SDKError as e:
    print(e)

# save resp as json to unstructured_api_test.json
with open("unstructured_api_test.json", "w") as f:
    f.write(json.dumps(resp, indent=4))
