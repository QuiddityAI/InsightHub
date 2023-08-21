import weaviate

from database_client.pubmed_data import get_pubmed_abstract


weaviate_server_url = "http://localhost:8080"
item_class_name = "Paper"

weaviate_client = None


def connect_to_weaviate():
    global weaviate_client
    weaviate_client = weaviate.Client(
        url = weaviate_server_url,
        # using anonymous connection, no auth needed
        # auth_client_secret=weaviate.AuthApiKey(api_key="YOUR-WEAVIATE-API-KEY"),
    )


def get_results_for_list(query, vector, limit):
    if not weaviate_client:
        connect_to_weaviate()
    response = (
        weaviate_client.query
        .get("Paper", ["title", "journal", "year", "pmid"])
        # .with_near_vector({
        #     "vector": embedding
        # })
        .with_hybrid(
            query = query,
            vector = vector
        )
        .with_limit(limit)
        .with_additional(["id", "distance", "score", "explainScore"]).do()
    )
    results = response["data"]["Get"][item_class_name]
    convert_to_absclust_db_format(results)
    return results


def get_results_for_map(query, vector, limit):
    if not weaviate_client:
        connect_to_weaviate()
    response = (
        weaviate_client.query
        .get("Paper", ["title", "journal", "year", "pmid"])
        .with_near_vector({
            "vector": vector
        })
        .with_limit(limit)
        .with_additional(["id", "distance", "score", "explainScore", "vector"]).do()
    )
    results = response["data"]["Get"][item_class_name]
    convert_to_absclust_db_format(results)
    return results


def convert_to_absclust_db_format(results: list[dict]) -> None:
    for item in results:
        item["issued_year"] = int(float(item.get("year", -1)))
        del item["year"]
        item["container_title"] = item["journal"]
        del item["journal"]
        if "vector" in item["_additional"]:
            item["vector"] = item["_additional"]["vector"]
            del item["_additional"]["vector"]
        item["distance"] = item["_additional"]["distance"]
        del item["_additional"]["distance"]
        item["abstract"] = get_pubmed_abstract(item["pmid"])
        item["DOI"] = item["pmid"]
