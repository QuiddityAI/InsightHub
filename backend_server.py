import time

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import weaviate
import numpy as np

# for tsne:
from sklearn.manifold import TSNE
import plotly.express as px


weaviate_server_url = "http://localhost:8080"
item_class_name = "Paper"

weaviate_client = weaviate.Client(
    url = weaviate_server_url,
    # using anonymous connection, no auth needed
    # auth_client_secret=weaviate.AuthApiKey(api_key="YOUR-WEAVIATE-API-KEY"),
)


def get_embedding(query: str) -> np.ndarray:
    url = 'http://localhost:55180/api/embedding/pubmedbert'
    data = {'query': query}
    result = requests.post(url, json=data)
    return np.asarray(result.json()["embedding"])


def get_search_results_for_list(queries: list[str], limit: int):
    results = []

    for query in queries:
        embedding = get_embedding(query)  # roughly 40ms on CPU, 10ms on GPU
          # 768 dimensions, float 16

        response = (
            weaviate_client.query
            .get("Paper", ["title", "journal"])
            # .with_near_vector({
            #     "vector": embedding
            # })
            .with_hybrid(
                query = query,
                vector = embedding[0]
            )
            .with_limit(limit // len(queries))
            .with_additional(["distance", "score", "explainScore"]).do()
        )
        results += response["data"]["Get"]["Paper"]

    return results


@app.route('/api/query', methods=['POST'])
def query():
    query = request.json.get("query")
    if not query:
        return jsonify({})

    timings = []
    t1 = time.time()
    search_results = get_search_results_for_list(query.split(" OR "), limit=10)
    t2 = time.time()
    timings.append({"part": "vector DB hybrid query", "duration": t2 - t1})

    result = {
        "items": search_results,
        "timings": timings,
    }
    return jsonify(result)


def get_search_results_for_map(queries: list[str], limit: int):
    results = []

    for query in queries:
        embedding = get_embedding(query)  # roughly 40ms on CPU, 10ms on GPU
          # 768 dimensions, float 16

        response = (
            weaviate_client.query
            .get("Paper", ["title"])
            .with_near_vector({
                "vector": embedding
            })
            .with_limit(limit // len(queries))
            .with_additional(["id", "distance", "vector"]).do()
        )
        results += response["data"]["Get"]["Paper"]

    return results


@app.route('/api/map', methods=['POST'])
def map_html():
    query = request.json.get("query")
    if not query:
        return jsonify({})

    timings = []
    t1 = time.time()
    elements = get_search_results_for_map(query.split(" OR "), limit=600)
    t2 = time.time()
    timings.append({"part": "vector DB pure vector query, limit 600", "duration": t2 - t1})

    vectors = []
    titles = []
    distances = []

    for e in elements:
        vectors.append(e["_additional"]["vector"])
        distances.append(e["_additional"]["distance"])
        titles.append(e["title"])

    features = np.asarray(vectors)  # shape 600x768
    t4 = time.time()
    timings.append({"part": "convert to numpy", "duration": t4 - t2})

    tsne = TSNE(n_components=2, random_state=0)  # instant
    projections = tsne.fit_transform(features)
    t6 = time.time()
    timings.append({"part": "fit transform", "duration": t6 - t4})

    plot_elements = [(projections[i][0], projections[i][1], titles[i]) for i in range(len(projections))]

    fig = px.scatter(
        plot_elements, x=0, y=1,
        text=titles,
        color=distances
    )
    t8 = time.time()
    timings.append({"part": "create plotly scatter plot", "duration": t8 - t6})

    fig.for_each_trace(lambda t: t.update(texttemplate="-", textposition='top center'))
    html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    t9 = time.time()
    timings.append({"part": "hide title for elements and convert to HTML", "duration": t9 - t8})

    js = html.split('<script type="text/javascript">')[2]
    js = js.replace("</script>", "").replace("</div>", "")

    result = {
        "html": html,
        "js": js,
        "timings": timings
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55123', debug=True)
