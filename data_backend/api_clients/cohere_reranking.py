import os
import logging

import cohere
from utils.helpers import load_env_file

load_env_file()


co = cohere.Client(os.environ.get('COHERE_API_KEY', "no_api_key"))


def get_reranking_results(query: str, texts: tuple[str, ...], top_n=10):
    # logging.warning(f"Using Cohere API to rerank {top_n} results for query: {query}")
    response = co.rerank(
        model = 'rerank-english-v3.0',  # multi-lingual is also available
        query = query,
        documents = texts,
        top_n = top_n,
        return_documents=False
    )
    return response
