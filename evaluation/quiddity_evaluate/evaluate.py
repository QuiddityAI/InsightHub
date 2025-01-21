import json
import tempfile
import time
import uuid

import boto3

from . import config
from .data_models import ExampleDocument


class QuiddityEvaluator:
    def __init__(self, client, dataset_id=11, collection_id=15, top_n=3, **kwargs):
        self.client = client
        self.dataset_id = dataset_id
        self.collection_id = collection_id
        self.top_n = top_n
        self.s3_client = boto3.client("s3", region_name=config.AWS_REGION)

    def evaluate(self, data_run_id: str):
        example_docs = self._load_docs(data_run_id)
        results = self._evaluate(example_docs)
        experiment_id = str(uuid.uuid4())
        evaluation_path = f"evaluations/{experiment_id}/results.json"
        metafatadata_path = f"evaluations/{experiment_id}/metadata.json"
        metadata = {"data_run_id": data_run_id, "experiment_id": experiment_id}
        self.s3_client.put_object(Bucket=config.BUCKET, Key=evaluation_path, Body=json.dumps(results))
        self.s3_client.put_object(Bucket=config.BUCKET, Key=metafatadata_path, Body=json.dumps(metadata))
        return results

    def _load_docs(self, run_id: str) -> list[ExampleDocument]:
        path = f"adversarial_data/{run_id}/generated.json"
        response = self.s3_client.get_object(Bucket=config.BUCKET, Key=path)
        input_data = json.loads(response["Body"].read().decode("utf-8"))
        examples = [ExampleDocument(**d) for d in input_data]
        return examples

    def _evaluate(self, example_docs: list[ExampleDocument]) -> list[dict]:

        with tempfile.TemporaryDirectory() as tmpdir:
            file_paths = []
            for doc in example_docs:
                _uuid = str(uuid.uuid4())
                file_path = f"{tmpdir}/{_uuid}.txt"
                file_paths.append(file_path)
                doc._uuid = _uuid
                with open(file_path, "w") as f:
                    f.write(doc.fulltext)

            doc_ids = self.client.upload_files(file_paths, dataset_id=self.dataset_id, block=True)
            print(f"Documents uploaded.")

        time.sleep(10)

        print("Performing search...")
        for doc in example_docs:
            docs = self.client.perform_search(
                dataset_id=self.dataset_id,
                user_input=doc.question,
                collection_id=self.collection_id,
                class_name="_default",
                candidates_per_step=self.top_n,
            )
            ids = [d.metadata.file_name.split(".")[0] for d in docs if d.metadata.file_name]
            print("Doc UUID", doc._uuid)
            print(f"Document IDs found: {ids}")
            is_correct = doc._uuid in ids
            doc.is_correct = is_correct
        self.client.remove_items(dataset_id=self.dataset_id, item_ids=doc_ids)
        return [doc.model_dump() for doc in example_docs]
