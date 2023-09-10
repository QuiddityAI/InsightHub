import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
import hdbscan

from utils.regex_tokenizer import tokenize
from utils.collect_timings import Timings


def clusterize_results(projections):
    clusterer = hdbscan.HDBSCAN(min_cluster_size=max(3, len(projections) // 50), min_samples=5)
    clusterer.fit(projections)
    return clusterer.labels_


def get_cluster_titles(cluster_labels, projections, results, descriptive_text_fields, timings: Timings):
    num_clusters = max(cluster_labels) + 1
    if num_clusters <= 0:
        return []
    texts_per_cluster = [""] * num_clusters
    points_per_cluster_x = [[] for i in range(num_clusters)]
    points_per_cluster_y = [[] for i in range(num_clusters)]
    results_by_cluster = [[] for i in range(num_clusters)]

    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = " ".join([results[result_index][field] for field in descriptive_text_fields])
        texts_per_cluster[cluster_index] += text
        points_per_cluster_x[cluster_index].append(projections[result_index][0])
        points_per_cluster_y[cluster_index].append(projections[result_index][1])
        results_by_cluster[cluster_index].append(results[result_index])
    timings.log("combining abstracts from search results")

    # highlight TF-IDF words:
    # tf_idf_helper = ClusterTitles()
    # vectorizer = TfidfVectorizer(stop_words="english")
    vectorizer = TfidfVectorizer(analyzer=tokenize, max_df=0.7)
    # vectorizer = TfidfVectorizer(analyzer=tf_idf_helper.tokenize)
    tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    cluster_data = []

    for cluster_index in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[cluster_index].toarray()[0])
        most_important_words = words[sort_indexes_of_important_words[-3:]][::-1]
        cluster_center = (float(np.mean(points_per_cluster_x[cluster_index])), float(np.mean(points_per_cluster_y[cluster_index])))
        cluster_title = ", ".join(list(most_important_words)) + f" ({len(results_by_cluster[cluster_index])})"
        cluster_data.append({"id": cluster_index, "title": cluster_title, "center": cluster_center})
    timings.log("Tf-Idf")

    return cluster_data
