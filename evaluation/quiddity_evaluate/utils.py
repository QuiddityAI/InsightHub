import json

import boto3
import dspy
from quiddity_evaluate.config import AWS_REGION, BUCKET


def upload_input_data_to_s3(input_data: list[dspy.Example], s3_path: str):
    # add json extension to the s3 path if it doesn't have one
    if s3_path.endswith(".json"):
        s3_path = s3_path[:-5]
    s3_path_data = f"input_data/{s3_path}/data.json"
    s3 = boto3.client("s3", region_name=AWS_REGION)
    input_data_dict = [d.toDict() for d in input_data]
    s3.put_object(Bucket=BUCKET, Key=s3_path_data, Body=json.dumps(input_data_dict))

    metadata = {"default_input_keys": list(input_data[0]._input_keys)}
    s3_path_metadata = f"input_data/{s3_path}/metadata.json"
    s3.put_object(Bucket=BUCKET, Key=s3_path_metadata, Body=json.dumps(metadata))
