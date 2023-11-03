from functools import partial
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
import hdbscan

from utils.regex_tokenizer import tokenize
from utils.collect_timings import Timings
from utils.dotdict import DotDict
from utils.helpers import normalize_array, join_text_source_fields


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
    scores_per_cluster = [[] for i in range(num_clusters)]
    normalized_scores = normalize_array(np.array([result['_score'] for result in results]))
    max_text_length = 512

    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = join_text_source_fields(results[result_index], descriptive_text_fields)
        texts_per_cluster[cluster_index] += text[:max_text_length]
        point_positions_per_cluster[cluster_index].append(positions[result_index])
        scores_per_cluster[cluster_index].append(normalized_scores[result_index])
    timings.log("collect information for clusters")

    # highlight TF-IDF words:
    # vectorizer = TfidfVectorizer(stop_words="english")

    # getting all words that appear in more than 80% of the clusters:
    count_vectorizer = CountVectorizer(tokenizer=tokenize, lowercase=False, strip_accents=None, min_df=0.8)
    count_vectorizer.fit_transform(texts_per_cluster)
    context_specific_ignore_words = count_vectorizer.get_feature_names_out()

    # using "tokenizer" instead of "analyzer" keeps the default preprocessor but also enables generation of ngrams
    # the default preprocessor only does lowercase conversion and accent stripping, so we can just disable those:
    context_specific_tokenize = partial(tokenize, context_specific_ignore_words=context_specific_ignore_words)
    vectorizer = TfidfVectorizer(tokenizer=context_specific_tokenize, lowercase=False, strip_accents=None, ngram_range=(1, 2), max_df=0.7)
    tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    cluster_data = []

    for cluster_index in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[cluster_index].toarray()[0])  # type: ignore
        # oversample 6 instead of 3, remove near duplicates, then take first 3:
        most_important_words_idx = list(sort_indexes_of_important_words[-6:][::-1])
        for i in range(len(most_important_words_idx) - 1, -1, -1):
            part = words[most_important_words_idx[i]]
            is_included_in_other = False
            longer_version = None
            other_location = None
            for j, other_part_idx in enumerate(most_important_words_idx):
                other_part = words[other_part_idx]
                if part is not other_part and part in other_part:
                    is_included_in_other = True
                    longer_version = other_part_idx
                    other_location = j
                    break
            if is_included_in_other:
                assert type(other_location) is int
                # put longer version at the first location and remove latter location:
                most_important_words_idx[min(i, other_location)] = longer_version
                del most_important_words_idx[max(i, other_location)]
        most_important_words = words[most_important_words_idx[:3]]
        # Note: score of each word could be obtained like this:
        # score = tf_idf_matrix[cluster_index].toarray()[0][word_idx]  # type: ignore
        cluster_center = np.mean(point_positions_per_cluster[cluster_index], axis=0).tolist()
        min_score = min(scores_per_cluster[cluster_index])
        max_score = max(scores_per_cluster[cluster_index])
        avg_score = np.mean(scores_per_cluster[cluster_index])
        cluster_title = ", ".join(list(most_important_words)) + f" ({len(point_positions_per_cluster[cluster_index])}x, {avg_score * 100:.0f}%)"
        cluster_title_html = f'<span style="font-weight: bold;">{most_important_words[0]}</span>, '
        cluster_title_html += ", ".join(list(most_important_words[1:])) + f" ({len(point_positions_per_cluster[cluster_index])}x, {avg_score * 100:.0f}%)"
        cluster_data.append({"id": cluster_index, "title": cluster_title, "title_html": cluster_title_html, "center": cluster_center,
                             "min_score": min_score, "max_score": max_score, "avg_score": avg_score})
    cluster_data = sorted(cluster_data, key=lambda cluster: cluster["avg_score"], reverse=True)
    timings.log("Tf-Idf for cluster titles")

    return cluster_data
