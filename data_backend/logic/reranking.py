import os
import logging
import json

import cohere
from diskcache import Cache

from logic.chat_and_extraction_common import get_context_for_each_item_in_search_results
from utils.helpers import load_env_file, DotDict

load_env_file()


co = cohere.Client(os.environ.get('COHERE_API_KEY', "no_api_key"))

cache = Cache("/data/quiddity_data/reranking_cache/")



def rerank(query: str, sorted_ids: list[tuple[int, str]], items_by_dataset: dict, top_n=10) -> list[tuple[int, str]]:
    cache_key = f"rerank_{query}_{json.dumps(sorted_ids[:top_n])}_{top_n}"
    if cache_key in cache:
        # logging.warning(f"Using reranking cache for query: {query}")
        result = cache.get(cache_key)
        assert isinstance(result, list)
        return result
    contexts = get_context_for_each_item_in_search_results(sorted_ids[:top_n], items_by_dataset)
    response = _get_reranking_results(query, tuple(contexts), top_n)
    new_indicies = [rerank_result.index for rerank_result in response.results]
    for rank, rerank_result in enumerate(response.results):
        idx = rerank_result.index
        item = items_by_dataset[sorted_ids[idx][0]][sorted_ids[idx][1]]
        if '_origins' not in item:
            item['_origins'] = []
        item['_origins'].append({'type': 'reranking', 'field': None,
                          'query': query, 'score': rerank_result.relevance_score, 'rank': rank + 1})

    sorted_ids[:top_n] = [sorted_ids[i] for i in new_indicies]
    cache.set(cache_key, sorted_ids, expire=3600*24*7*4)  # 4 weeks
    return sorted_ids


def _get_reranking_results(query: str, texts: tuple[str, ...], top_n=10):
    # logging.warning(f"Using Cohere API to rerank {top_n} results for query: {query}")
    response = co.rerank(
        model = 'rerank-english-v3.0',  # multi-lingual is also available
        query = query,
        documents = texts,
        top_n = top_n,
        return_documents=False
    )
    return response
