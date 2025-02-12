import importlib
import inspect
import json
import tempfile

import boto3
import dspy
import petname
from quiddity_evaluate import config


class ModelRegistry:
    def __init__(self):
        self.s3_client = boto3.client("s3", region_name=config.AWS_REGION)

    def _save_model_as_pickle(self, model: dspy.Module):
        model_petname = petname.Generate(2, "-")
        class_name = model.__class__.__name__
        model_id = f"{class_name.lower()}_{model_petname}"
        model_s3_path = f"models/{model_id}/"

        # save model to temp path
        with tempfile.TemporaryDirectory() as temp_dir:
            model.save(temp_dir, save_program=True)
            self.s3_client.upload_file(f"{temp_dir}/metadata.json", config.BUCKET, model_s3_path + "metadata.json")
            self.s3_client.upload_file(f"{temp_dir}/program.pkl", config.BUCKET, model_s3_path + "program.pkl")
        return model_id

    def _load_model_as_pickle(self, model_name: str) -> dspy.Module:
        model_s3_path = f"models/{model_name}/"
        with tempfile.TemporaryDirectory() as temp_dir:
            self.s3_client.download_file(config.BUCKET, model_s3_path + "metadata.json", f"{temp_dir}/metadata.json")
            self.s3_client.download_file(config.BUCKET, model_s3_path + "program.pkl", f"{temp_dir}/program.pkl")
            model = dspy.load(f"{temp_dir}")
        return model

    def _load_json_from_s3(self, s3_path: str) -> dict:
        obj = self.s3_client.get_object(Bucket=config.BUCKET, Key=s3_path)
        return json.loads(obj["Body"].read().decode("utf-8"))

    def load_model(self, model_name: str) -> dspy.Module:
        return self._load_model_as_pickle(model_name)

    def save_model(self, model: dspy.Module) -> str:
        return self._save_model_as_pickle(model)

    # highly experimental code for saving / laoding models as .py files
    # not ready for real use yet
    # def load_model(self, model_name: str) -> dspy.Module:
    #     model_s3_path = f"models/{model_name}/"
    #     metadata = self._load_json_from_s3(model_s3_path + "metadata.json")
    #     state = self._load_json_from_s3(model_s3_path + "state.json")

    #     with tempfile.TemporaryDirectory() as temp_dir:
    #         self.s3_client.download_file(config.BUCKET, model_s3_path + "source.py", f"{temp_dir}/source.py")
    #         spec = importlib.util.spec_from_file_location("model_definition", f"{temp_dir}/source.py")
    #         try:
    #             # Try executing the module and ignore unresolved imports
    #             spec.loader.exec_module(model_module)
    #         except ImportError as e:
    #             print(f"Warning: Ignored an ImportError: {e}")
    #         model_module = importlib.util.module_from_spec(spec)
    #         # spec.loader.exec_module(model_module)
    #     model_class = getattr(model_module, metadata["class_name"])
    #     model = model_class()
    #     model.load_state(state)
    #     return model

    # def save_model(self, model: dspy.Module):
    #     model_petname = petname.Generate(2, "-")
    #     class_name = model.__class__.__name__
    #     model_id = f"{class_name.lower()}_{model_petname}"
    #     model_s3_path = f"models/{model_id}/"

    #     model_source_path = inspect.getfile(model.__class__)
    #     state = json.dumps(model.dump_state())

    #     metadata = json.dumps(
    #         {
    #             "class_name": class_name,
    #             "model_id": model_id,
    #         }
    #     )
    #     self.s3_client.upload_file(model_source_path, config.BUCKET, model_s3_path + "source.py")
    #     self.s3_client.put_object(Bucket=config.BUCKET, Key=model_s3_path + "state.json", Body=state)
    #     self.s3_client.put_object(Bucket=config.BUCKET, Key=model_s3_path + "metadata.json", Body=metadata)
    #     return model_id
