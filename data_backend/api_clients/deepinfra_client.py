from concurrent.futures import ThreadPoolExecutor
import json
import os
from typing import Iterable

from utils.helpers import load_env_file
import requests

load_env_file()


DEEPINFRA_API_KEY = os.environ.get('DEEPINFRA_API_KEY', "no_api_key")


def get_embeddings(texts: list[str], model_name: str,):
    batch_size = 512
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    #t1 = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        embedding_batches = executor.map(
            lambda batch: _get_embeddings_batch(batch, model_name),
            batches
        )
    #logging.warning(f"Total time for {len(texts)} texts: {time.time() - t1:.2f} s")
    embeddings = [embedding for embedding_batch in embedding_batches for embedding in embedding_batch]
    return embeddings


def _get_embeddings_batch(texts: Iterable[str], model_name: str):
    model_to_url = {
        'intfloat/e5-base-v2': 'https://api.deepinfra.com/v1/inference/intfloat/e5-base-v2',
    }
    url = model_to_url[model_name]
    headers = {
        'Authorization': f'bearer {DEEPINFRA_API_KEY}',
        'Accept-Encoding': 'gzip, deflate, br',  # doesn't change much, gzip is already the default, but just to be sure
    }
    data = {
        'inputs': json.dumps(texts)
    }
    #logging.warning(f"Data size in MB: {len(data['inputs']) / 1024 / 1024:.2f} MB")
    #t1 = time.time()
    response = requests.post(url, headers=headers, files=data)
    #actual_time = time.time() - t1
    result = response.json()
    #compute_time = int(result.get("inference_status", {}).get("runtime_ms", 0)) / 1000
    #logging.warning(f"Deepinfra compute time vs request time: {compute_time:.2f} vs {actual_time:.2f} s")
    #for key in result:
    #    if key not in ["embeddings"]:
    #        logging.warning(f"Deepinfra result: {key}: {result[key]}")
    #logging.warning(f"Result size in MB: {len(json.dumps(result)) / 1024 / 1024:.2f} MB")
    return result["embeddings"]
