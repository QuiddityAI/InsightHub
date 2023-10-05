import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
import hdbscan

from utils.regex_tokenizer import tokenize
from utils.collect_timings import Timings
from utils.dotdict import DotDict


def clusterize_results(projections, clusterizer_parameters: DotDict):
    min_cluster_size = max(3, len(projections) // 50) if clusterizer_parameters.get("min_cluster_size", -1) <= 0 else clusterizer_parameters.min_cluster_size
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                min_samples=clusterizer_parameters.get("min_samples", 5),
                                cluster_selection_method="leaf" if clusterizer_parameters.get("leaf_mode", False) else "eom",
                                )
    clusterer.fit(projections)
    return clusterer.labels_


def get_cluster_titles(cluster_labels, positions, results, descriptive_text_fields, timings: Timings):
    num_clusters = max(cluster_labels) + 1
    if num_clusters <= 0:
        return []
    texts_per_cluster = [""] * num_clusters
    point_positions_per_cluster = [[] for i in range(num_clusters)]

    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = " ".join([results[result_index].get(field, "") for field in descriptive_text_fields])
        texts_per_cluster[cluster_index] += text
        point_positions_per_cluster[cluster_index].append(positions[result_index])
    timings.log("collect information for clusters")

    # highlight TF-IDF words:
    # vectorizer = TfidfVectorizer(stop_words="english")
    vectorizer = TfidfVectorizer(analyzer=tokenize, max_df=0.7)
    tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    cluster_data = []

    for cluster_index in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[cluster_index].toarray()[0])  # type: ignore
        most_important_words = words[sort_indexes_of_important_words[-3:]][::-1]
        cluster_center = np.mean(point_positions_per_cluster[cluster_index], axis=0).tolist()
        cluster_title = ", ".join(list(most_important_words)) + f" ({len(point_positions_per_cluster[cluster_index])})"
        cluster_data.append({"id": cluster_index, "title": cluster_title, "center": cluster_center})
    timings.log("Tf-Idf for cluster titles")

    return cluster_data
