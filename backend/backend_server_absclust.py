import time
import re
from functools import lru_cache

from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import numpy as np
from tqdm import tqdm

# for tsne:
# from sklearn.manifold import TSNE
import umap
import plotly.express as px

from sklearn.feature_extraction.text import TfidfVectorizer
import hdbscan


from utils.model_client import get_embedding, get_openai_embedding_batch, save_embedding_cache
from utils.absclust_client import get_absclust_search_results, save_search_cache


def get_search_results_for_list(queries: list[str], limit: int):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid][:10]
            continue

        results_part = get_absclust_search_results(query, limit)
        results += results_part

    save_search_cache()

    return results


words_ignored_for_highlighting = ("on", "in", "using", "with", "the", "a", "of")


def enrich_search_results(results, query):
    corpus = []

    for i, item in enumerate(results):
        title = item["title"]
        abstract = item["abstract"]
        corpus.append(title + " " + abstract)
        for word in query.split(" "):
            if word in words_ignored_for_highlighting:
                continue
            replacement = '<span class="font-bold">\\1</span>'
            title = re.sub(f"\\b({re.escape(word)})\\b", replacement, title, flags=re.IGNORECASE)
            abstract = re.sub(f"\\b({re.escape(word)})\\b", replacement, abstract, flags=re.IGNORECASE)
        results[i]["title"] = title
        results[i]["abstract"] = abstract.replace("\n", "<br>")

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
    return _query(request.json.get("query"))


@lru_cache()
def _query(query):
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
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid]
            continue

        results_part = get_absclust_search_results(query, limit)

        query_embedding = get_embedding(query)

        # using the code below leads to broken vectors for some reasons:
        # texts = [item.get("title", "") + " " + item.get("abstract", "") for item in results_part]
        # chunk_size = 30  # 30 -> 2.7GB GPU RAM (almost linear)
        # embeddings = np.zeros((0, 768))
        # for i in range(0, len(texts), chunk_size):
        #     embeddings = np.append(embeddings, get_embedding(texts[i:i+chunk_size]), axis=0)

        #texts = {item["DOI"]: item.get("title", "") + " " + item.get("abstract", "")[:2000] for item in results_part}
        #embeddings = get_openai_embedding_batch(texts)
        #save_embedding_cache()

        for item in tqdm(results_part):
            #item_embedding = embeddings[item["DOI"]]
            item_embedding = get_embedding(item.get("title", "") + " " + item.get("abstract", ""), item["DOI"])
            item["vector"] = item_embedding
            item["distance"] = np.dot(query_embedding, item_embedding)

        results += results_part

    save_search_cache()
    save_embedding_cache()

    return results


def cluster_results(projections):
    clusterer = hdbscan.HDBSCAN(min_cluster_size=max(3, len(projections) // 50), min_samples=5)
    clusterer.fit(projections)
    return clusterer.labels_

last_cluster_id = 0
cluster_cache = {}  # cluster_id -> search_results


def get_cluster_titles(cluster_labels, projections, results, timings):
    global last_cluster_id, cluster_cache
    num_clusters = max(cluster_labels) + 1
    if num_clusters <= 0:
        return [], [], []
    texts_per_cluster = [""] * num_clusters
    points_per_cluster_x = [[] for i in range(num_clusters)]
    points_per_cluster_y = [[] for i in range(num_clusters)]
    results_by_cluster = [[] for i in range(num_clusters)]

    t1 = time.time()
    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = results[result_index]["title"] + " " + results[result_index]["abstract"]
        texts_per_cluster[cluster_index] += text
        points_per_cluster_x[cluster_index].append(projections[result_index][0])
        points_per_cluster_y[cluster_index].append(projections[result_index][1])
        results_by_cluster[cluster_index].append(results[result_index])
    t2 = time.time()
    timings.append({"part": "getting abstracts from disk", "duration": t2 - t1})

    # highlight TF-IDF words:
    vectorizer = TfidfVectorizer(stop_words="english")
    tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    cluster_titles = []
    cluster_centers = []
    cluster_uids = []

    for cluster_index in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[cluster_index].toarray()[0])
        most_important_words = words[sort_indexes_of_important_words[-3:]][::-1]
        cluster_titles.append(list(most_important_words))
        cluster_centers.append((np.mean(points_per_cluster_x[cluster_index]), np.mean(points_per_cluster_y[cluster_index])))
        last_cluster_id += 1
        cluster_uid = str(last_cluster_id)
        cluster_cache[cluster_uid] = results_by_cluster[cluster_index]
        cluster_uids.append({"cluster_id": cluster_uid, "cluster_title": ", ".join(list(most_important_words)) + f" ({len(results_by_cluster[cluster_index])})"})
    t3 = time.time()
    timings.append({"part": "Tf-Idf", "duration": t3 - t2})

    return cluster_titles, cluster_centers, cluster_uids


@app.route('/api/map', methods=['POST'])
def map_html():
    query = request.json.get("query")
    return _map_html(query)


@lru_cache()
def _map_html(query):
    if not query:
        return jsonify({})

    timings = []
    t1 = time.time()
    elements = get_search_results_for_map(query.split(" OR "), limit=3000)
    t2 = time.time()
    timings.append({"part": "vector DB pure vector query, limit 600", "duration": t2 - t1})

    vectors = []
    titles = []
    distances = []

    for e in elements:
        vectors.append(e["vector"])
        distances.append(e["distance"])
        titles.append(e.get("title", ""))

    features = np.asarray(vectors)  # shape 600x768
    t4 = time.time()
    timings.append({"part": "convert to numpy", "duration": t4 - t2})

    # tsne = TSNE(n_components=2, random_state=0)  # instant
    # projections = tsne.fit_transform(features)
    projections = umap.UMAP(random_state=99, min_dist=0.05).fit_transform(features)
    t6 = time.time()
    timings.append({"part": "UMAP fit transform", "duration": t6 - t4})
    cluster_labels = cluster_results(projections)
    cluster_titles, cluster_centers, cluster_uids = get_cluster_titles(cluster_labels, projections, elements, timings)
    t7 = time.time()

    plot_elements = [(projections[i][0], projections[i][1], titles[i]) for i in range(len(projections))]

    fig = px.scatter(
        plot_elements, x=0, y=1,
        text=titles,
        #color=distances,
        color=cluster_labels,
        #size=distances,  # needs normalization with min size
    )
    t8 = time.time()
    timings.append({"part": "create plotly scatter plot", "duration": t8 - t7})

    for i in range(len(cluster_titles)):
        cluster_title = ", ".join(cluster_titles[i])
        annotation_html = f'<b>{cluster_title}</b>'
        fig.add_annotation(x=cluster_centers[i][0], y=cluster_centers[i][1],
            text=annotation_html, bgcolor="white", opacity=0.85)

    fig.for_each_trace(lambda t: t.update(texttemplate="<br>", textposition='top center', textfont = {'color': "rgba(0, 0, 0, 0)"}))
    fig.update_layout(showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update(layout_coloraxis_showscale=False)
    fig.update_layout(margin=dict(l = 0, r = 0, t = 0, b = 0))
    html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    t9 = time.time()
    timings.append({"part": "hide title for elements and convert to HTML", "duration": t9 - t8})

    js = html.split('<script type="text/javascript">')[2]
    js = js.replace("</script>", "").replace("</div>", "")

    result = {
        "html": html,
        "js": js,
        "cluster_uids": cluster_uids,
        "timings": timings
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55123', debug=True)
