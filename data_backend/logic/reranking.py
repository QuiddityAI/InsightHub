import os
import logging

import cohere

from logic.chat_and_extraction_common import get_context_for_each_item_in_search_results
from utils.helpers import load_env_file, DotDict

load_env_file()


co = cohere.Client(os.environ.get('COHERE_API_KEY', "no_api_key"))


def rerank(search_settings: DotDict, sorted_ids: list[tuple[int, str]], items_by_dataset: dict, top_n=10) -> list[tuple[int, str]]:
    contexts = get_context_for_each_item_in_search_results(sorted_ids[:top_n], items_by_dataset)
    query = search_settings.all_field_query
    response = co.rerank(
        model = 'rerank-english-v3.0',  # multi-lingual is also available
        query = query,
        documents = contexts,
        top_n = top_n,
        return_documents=False
    )
    new_indicies = [rerank_result.index for rerank_result in response.results]
    for rank, rerank_result in enumerate(response.results):
        idx = rerank_result.index
        item = items_by_dataset[sorted_ids[idx][0]][sorted_ids[idx][1]]
        if '_origins' not in item:
            item['_origins'] = []
        item['_origins'].append({'type': 'reranking', 'field': None,
                          'query': query, 'score': rerank_result.relevance_score, 'rank': rank + 1})

    sorted_ids[:top_n] = [sorted_ids[i] for i in new_indicies]
    return sorted_ids
