import logging
import os

import cohere

co = cohere.Client(os.environ.get("COHERE_API_KEY", "no_api_key"))


def get_reranking_results(query: str, texts: tuple[str, ...], top_n=10):
    # logging.warning(f"Using Cohere API to rerank {top_n} results for query: {query}")
    try:
        response = co.rerank(
            model="rerank-v3.5",  # 3.5 combines english and multilingual
            query=query,
            documents=texts,
            top_n=top_n,
            return_documents=False,
        )
    except Exception as e:
        logging.error(f"Failed to rerank query: {query} with error: {e}")
        response = cohere.RerankResponse(
            results=[
                cohere.RerankResponseResultsItem(index=i, relevance_score=0.0) for i in range(min(len(texts), top_n))
            ]
        )
    return response
