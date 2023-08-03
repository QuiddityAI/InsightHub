import mmap
from pathlib import Path
import pickle
import time
import re

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import weaviate
import numpy as np

# for tsne:
# from sklearn.manifold import TSNE
import umap
import plotly.express as px

from sklearn.feature_extraction.text import TfidfVectorizer
import hdbscan


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
            .get("Paper", ["title", "journal", "year", "pmid"])
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


data_root = Path('/data/pubmed_embeddings/')
abstracts_path = data_root / 'pubmed_landscape_abstracts.csv'

with open(data_root / "pmid_to_pos_and_length.pkl", "rb") as f:
    pmid_to_abstract_pos_and_length = pickle.load(f)

with open(abstracts_path, "r+") as f:
    abstracts_mmap_file = mmap.mmap(f.fileno(), 0)


def get_pubmed_abstract(pmid):
    pos, length = pmid_to_abstract_pos_and_length[pmid]
    abstract = abstracts_mmap_file[pos : pos + length].decode()
    abstract = abstract.strip('"')
    return abstract


def get_pubmed_abstract_online(pmid: str):
    try:
        result = requests.get(f"http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=text&rettype=abstract")
        raw_xml = result.text
        abstract = raw_xml  # .split("<AbstractText>")[1].split("</AbstractText>")[0]
    except IndexError:
        return ""
    except Exception as e:
        print(e)
        return ""
    return abstract


words_ignored_for_highlighting = ("on", "in", "using", "with", "the", "a")


def enrich_search_results(results, query):
    corpus = []

    for i, item in enumerate(results):
        title = item["title"]
        abstract = get_pubmed_abstract(item["pmid"])
        corpus.append(title + " " + abstract)
        for word in query.split(" "):
            if word in words_ignored_for_highlighting:
                continue
            replacement = '<span class="font-bold">\\1</span>'
            title = re.sub(f"\\b({re.escape(word)})\\b", replacement, title, flags=re.IGNORECASE)
            abstract = re.sub(f"\\b({re.escape(word)})\\b", replacement, abstract, flags=re.IGNORECASE)
        results[i]["title"] = title
        results[i]["abstract"] = abstract.replace("\n", "<br>")
        results[i]["year"] = int(float(item["year"]))

    # highlight TF-IDF words:
    vectorizer = TfidfVectorizer(stop_words="english")
    tf_idf_matrix = vectorizer.fit_transform(corpus)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    for i, item in enumerate(results):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[i].toarray()[0])
        most_important_words = words[sort_indexes_of_important_words[-5:]][::-1]
        results[i]["most_important_words"] = list(most_important_words)
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

    search_results = enrich_search_results(search_results, query)
    t3 = time.time()
    timings.append({"part": "enriching results", "duration": t3 - t2})

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
            .get("Paper", ["title", "pmid"])
            .with_near_vector({
                "vector": embedding
            })
            .with_limit(limit // len(queries))
            .with_additional(["id", "distance", "vector"]).do()
        )
        results += response["data"]["Get"]["Paper"]

    return results


def cluster_results(projections):
    clusterer = hdbscan.HDBSCAN()
    clusterer.fit(projections)
    return clusterer.labels_


def get_cluster_titles(cluster_labels, projections, results):
    num_clusters = max(cluster_labels) + 1
    texts_per_cluster = [""] * num_clusters
    points_per_cluster_x = [[] for i in range(num_clusters)]
    points_per_cluster_y = [[] for i in range(num_clusters)]

    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = results[result_index]["title"] + " " + get_pubmed_abstract(results[result_index]["pmid"])
        texts_per_cluster[cluster_index] += text
        points_per_cluster_x[cluster_index].append(projections[result_index][0])
        points_per_cluster_y[cluster_index].append(projections[result_index][1])

    # highlight TF-IDF words:
    vectorizer = TfidfVectorizer(stop_words="english")
    tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    cluster_titles = []
    cluster_centers = []

    for cluster_index in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[cluster_index].toarray()[0])
        most_important_words = words[sort_indexes_of_important_words[-3:]][::-1]
        cluster_titles.append(list(most_important_words))
        cluster_centers.append((np.mean(points_per_cluster_x[cluster_index]), np.mean(points_per_cluster_y[cluster_index])))

    return cluster_titles, cluster_centers


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

    # tsne = TSNE(n_components=2, random_state=0)  # instant
    # projections = tsne.fit_transform(features)
    projections = umap.UMAP().fit_transform(features)
    cluster_labels = cluster_results(projections)
    cluster_titles, cluster_centers = get_cluster_titles(cluster_labels, projections, elements)
    t6 = time.time()
    timings.append({"part": "fit transform", "duration": t6 - t4})

    plot_elements = [(projections[i][0], projections[i][1], titles[i]) for i in range(len(projections))]

    fig = px.scatter(
        plot_elements, x=0, y=1,
        text=titles,
        #color=distances,
        color=cluster_labels,
    )
    t8 = time.time()
    timings.append({"part": "create plotly scatter plot", "duration": t8 - t6})

    for i in range(len(cluster_titles)):
        fig.add_annotation(x=cluster_centers[i][0], y=cluster_centers[i][1],
            text=", ".join(cluster_titles[i]))

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
