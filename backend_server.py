import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import weaviate
import numpy as np


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


@app.route('/')
def index():
    return '<h1>Hello!</h1>'


@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify([])

    t1 = time.time()
    embedding = get_embedding(query)
    t2 = time.time()
    generate_embedding_duration = t2 - t1

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
        .with_limit(10)
        .with_additional(["distance", "score", "explainScore"]).do()
    )
    t3 = time.time()
    vector_db_query = t3 - t2

    result = {
        "items": response["data"]["Get"]["Paper"],
        "timings": [
            {"part": "generate_embedding_duration", "duration": generate_embedding_duration},
            {"part": "vector_db_query", "duration": vector_db_query},
        ]
    }
    return jsonify(result)


@app.route('/api/map', methods=['POST'])
def map_html():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify([])

    embedding = get_embedding(query)

    timings = []
    t1 = time.time()
    response = (
        weaviate_client.query
        .get("Paper", ["title"])
        .with_near_vector({
            "vector": embedding
        })
        .with_limit(600)
        .with_additional(["id", "distance"]).do()
    )
    elements = response["data"]["Get"]["Paper"]
    t2 = time.time()
    timings.append({"part": "vector db query", "duration": t2 - t1})

    vectors = []
    titles = []
    distances = []

    for e in elements:
        d = weaviate_client.data_object.get_by_id(
            uuid=e["_additional"]["id"],
            class_name='Paper',
            with_vector=True
        )
        vectors.append(d["vector"])
        distances.append(e["_additional"]["distance"])
        titles.append(e["title"])
    t3 = time.time()
    timings.append({"part": "getting vectors", "duration": t3 - t2})

    from sklearn.manifold import TSNE
    import plotly.express as px

    features = np.asarray(vectors)
    print(features.shape)
    t4 = time.time()
    timings.append({"part": "convert to numpy", "duration": t4 - t3})

    tsne = TSNE(n_components=2, random_state=0)
    t5 = time.time()
    timings.append({"part": "TSNE ctor", "duration": t5 - t4})
    projections = tsne.fit_transform(features)
    t6 = time.time()
    timings.append({"part": "fit transform", "duration": t6 - t5})
    x = [(projections[i][0], projections[i][1], titles[i]) for i in range(len(projections))]
    t7 = time.time()
    timings.append({"part": "rearrange", "duration": t7 - t6})

    fig = px.scatter(
        x, x=0, y=1,
        text=titles,
        color=distances
    )
    t8 = time.time()
    timings.append({"part": "scatter()", "duration": t8 - t7})
    fig.for_each_trace(lambda t: t.update(texttemplate="-", textposition='top center'))
    t9 = time.time()
    timings.append({"part": "for each trace()", "duration": t9 - t8})
    html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    t10 = time.time()
    timings.append({"part": "to_html", "duration": t10- t9})
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
