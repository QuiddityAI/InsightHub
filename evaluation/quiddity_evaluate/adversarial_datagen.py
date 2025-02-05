import json
from typing import Any, List

import boto3
import dspy
import petname

from . import config
from .data_models import ExampleDocument
from .model_registry import ModelRegistry

registry = ModelRegistry()


class AdversarialDocGenerator:
    def __init__(self, adversarial_model_name: str):
        """
        Initializes the adversarial docs generator.
        """
        self.adversarial_model_name = adversarial_model_name
        self.adversarial_model = registry.load_model(adversarial_model_name)
        self.s3_client = boto3.client("s3", region_name=config.AWS_REGION)

    def _load_json_from_s3(self, s3_path: str) -> dict:
        obj = self.s3_client.get_object(Bucket=config.BUCKET, Key=s3_path)
        return json.loads(obj["Body"].read().decode("utf-8"))

    def _load_input_examples(self, input_data_name: str, input_keys=None) -> List[dspy.Example]:
        """
        Loads the input data from the given S3 path.
        """
        if input_data_name.endswith(".json"):
            input_data_name = input_data_name[:-5]
        input_data_path = f"input_data/{input_data_name}"
        data = self._load_json_from_s3(input_data_path + "/data.json")
        metadata = self._load_json_from_s3(input_data_path + "/metadata.json")
        input_keys = metadata.get("default_input_keys") if input_keys is None else input_keys
        if input_keys is None:
            raise ValueError("Input keys must be provided.")
        return [dspy.Example(**d).with_inputs(*input_keys) for d in data]

    def generate_and_save(self, input_data_path: str, num_threads=8):
        """
        Generates adversarial examples for the given input data and saves them to S3.
        """
        examples = self._load_input_examples(input_data_path)
        generated = self._generate(examples, num_threads)
        run_id = petname.Generate(3, " ").replace(" ", "-")
        metadata = {"input_data_path": input_data_path}
        self._save_to_s3(generated, run_id, metadata)

    def _generate(self, examples: list[dspy.Example], num_threads=8) -> List[ExampleDocument]:
        """
        Generates adversarial examples for the given list of examples.
        """
        parallel = dspy.Parallel(num_threads=num_threads)
        generated = parallel([(self.adversarial_model, e) for e in examples])
        res = [ExampleDocument(question=g[0], fulltext=g[1]) for g in generated]
        return res

    def _save_to_s3(self, docs: List[ExampleDocument], run_id: str, metadata: dict) -> None:
        """
        Saves the generated data to the given S3 path.
        """
        path = f"adversarial_data/{run_id}/generated.json"
        data = [d.model_dump() for d in docs]
        self.s3_client.put_object(Bucket=config.BUCKET, Key=path, Body=json.dumps(data))

        metadata_path = f"adversarial_data/{run_id}/metadata.json"
        metadata = metadata | {"model_name": self.adversarial_model_name, "run_id": run_id}
        self.s3_client.put_object(Bucket=config.BUCKET, Key=metadata_path, Body=json.dumps(metadata))
