from functools import partial
import logging
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
import hdbscan

from ..utils.regex_tokenizer import tokenize
from ..utils.collect_timings import Timings
from ..utils.dotdict import DotDict
from ..utils.helpers import normalize_array, join_text_source_fields, get_field_from_all_items


def clusterize_results(projections, clusterizer_parameters: DotDict):
    min_cluster_size = max(3, len(projections) // 50) if clusterizer_parameters.get("min_cluster_size", -1) <= 0 else clusterizer_parameters.min_cluster_size
    max_cluster_size = clusterizer_parameters.get("max_cluster_size", 0.5) * len(projections)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                max_cluster_size=max_cluster_size,
                                min_samples=clusterizer_parameters.get("min_samples", 5),
                                cluster_selection_method="leaf" if clusterizer_parameters.get("leaf_mode", False) else "eom",
                                )
    try:
        clusterer.fit(projections)
    except ValueError as e:
        # this might happen when there are too few points to cluster
        logging.warning(f"Error in HDBSCAN: {e}")
        return np.zeros(len(projections), dtype=int) - 1
    return clusterer.labels_


def get_cluster_titles(cluster_id_per_point, positions, sorted_ids: list[tuple[str, str]], items_by_dataset: dict[str, dict[str, dict]], datasets: dict[str, DotDict], result_language: str | None, timings: Timings):
    num_clusters: int = max(cluster_id_per_point) + 1
    if num_clusters <= 0:
        return []
    texts_per_cluster: list[str] = [""] * num_clusters
    texts_per_item: list[str] = []
    point_positions_per_cluster = [[] for i in range(num_clusters)]
    scores_per_cluster = [[] for i in range(num_clusters)]
    normalized_scores = normalize_array(np.array(get_field_from_all_items(items_by_dataset, sorted_ids, "score", 0.0)))
    max_text_length = 512
    field_boundary_indicator = "_stop_"
    field_boundary_indicator_padded = " _stop_ "

    for result_index, cluster_id in enumerate(cluster_id_per_point):
        if cluster_id <= -1: continue
        ds_id, item_id = sorted_ids[result_index]
        descriptive_text_fields = datasets[ds_id].get('schema', {}).get("descriptive_text_fields", [])
        text = join_text_source_fields(items_by_dataset[ds_id][item_id], descriptive_text_fields, field_boundary_indicator_padded)
        texts_per_item.append(text)
        texts_per_cluster[cluster_id] += f" {field_boundary_indicator} {text[:max_text_length]}"
        point_positions_per_cluster[cluster_id].append(positions[result_index])
        scores_per_cluster[cluster_id].append(normalized_scores[result_index])
    timings.log("collect information for clusters")

    # IDEA: get top words from all clusters, then subtract all other vectors from vector from current
    # cluster, then take word closest to that vector

    dataset_specific_ignore_words: set = set()
    use_lower_case = True
    for dataset in datasets.values():
        advanced_options = dataset.get("advanced_options", {})
        ignore_words = advanced_options.get("ignore_words", [])
        dataset_specific_ignore_words.update(ignore_words)
        if not advanced_options.get("use_lower_case", True):
            use_lower_case = False

    # getting all words that appear in more than 50% of the items:
    context_specific_tokenize = partial(tokenize, context_specific_ignore_words=dataset_specific_ignore_words, use_lower_case=use_lower_case)
    count_vectorizer = CountVectorizer(tokenizer=tokenize, lowercase=False, strip_accents=None, min_df=0.5)
    try:
        count_vectorizer.fit_transform(texts_per_item)
    except ValueError as e:
        # this might happen when there are no terms appearing in more than 50% of the items
        logging.warning(f"Error in CountVectorizer: {e}")
        context_specific_ignore_words = []
    else:
        context_specific_ignore_words = list(count_vectorizer.get_feature_names_out())

    if field_boundary_indicator in context_specific_ignore_words:
        context_specific_ignore_words.remove(field_boundary_indicator)
    context_specific_ignore_words = set(x.lower() for x in context_specific_ignore_words)

    # using "tokenizer" instead of "analyzer" keeps the default preprocessor but also enables generation of ngrams
    # the default preprocessor only does lowercase conversion and accent stripping, so we can just disable those:
    all_ignore_words = context_specific_ignore_words | dataset_specific_ignore_words  # type: ignore
    if result_language and result_language in LANGUAGE_IGNORE_WORDS:
        all_ignore_words |= set(LANGUAGE_IGNORE_WORDS[result_language])
    context_specific_tokenize = partial(tokenize, context_specific_ignore_words=all_ignore_words, use_lower_case=use_lower_case)
    vectorizer = TfidfVectorizer(tokenizer=context_specific_tokenize, lowercase=False, strip_accents=None, ngram_range=(1, 2), max_df=0.7)
    try:
        vectorizer.fit(texts_per_cluster)
    except ValueError as e:
        # this might happend when there are no terms appearing in more than 70% of the clusters (?)
        logging.warning(f"Error in TfidfVectorizer: {e}")
        # try again without max_df limit:
        vectorizer = TfidfVectorizer(tokenizer=context_specific_tokenize, lowercase=False, strip_accents=None, ngram_range=(1, 2))
        vectorizer.fit(texts_per_cluster)

    # To prevent the generation of n-grams across different source fields, a specific token
    # is inserted between the fields ("_stop_", see join_text_source_fields() ).
    # We now remove any 2-grams from the vocabulary that contain the field boundary indicator "_stop_":
    for voc in list(vectorizer.vocabulary_.keys()):
        if field_boundary_indicator in voc:
            del vectorizer.vocabulary_[voc]
    # recreate the TfidfVectorizer object with the cleaned-up vocabulary:
    vectorizer = TfidfVectorizer(tokenizer=context_specific_tokenize, lowercase=False, strip_accents=None, ngram_range=(1, 2), max_df=0.7, vocabulary=vectorizer.vocabulary_.keys())

    cluster_data = []

    try:
        tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    except ValueError as e:
        logging.warning(f"Error in TfidfVectorizer.fit_transform: {e}")
        # this might happen when there are clusters without common words (?)
        for cluster_id in range(num_clusters):
            title = f"Cluster {cluster_id + 1}"
            cluster_center = np.mean(point_positions_per_cluster[cluster_id], axis=0).tolist()
            min_score = min(scores_per_cluster[cluster_id])
            max_score = max(scores_per_cluster[cluster_id])
            avg_score = np.mean(scores_per_cluster[cluster_id])
            cluster_data.append({"id": cluster_id, "title": title, "title_html": title, "center": cluster_center,
                             "min_score": min_score, "max_score": max_score, "avg_score": avg_score})
        return cluster_data
    words = vectorizer.get_feature_names_out()

    for cluster_id in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        word_weights = tf_idf_matrix[cluster_id].toarray()[0]  # type: ignore
        sort_indexes_of_important_words = np.argsort(word_weights)  # type: ignore
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
        cluster_center = np.mean(point_positions_per_cluster[cluster_id], axis=0).tolist()
        min_score = min(scores_per_cluster[cluster_id])
        max_score = max(scores_per_cluster[cluster_id])
        avg_score = np.mean(scores_per_cluster[cluster_id])
        cluster_title = ", ".join(list(most_important_words)) + f" ({len(point_positions_per_cluster[cluster_id])}x, {avg_score * 100:.0f}%)"
        cluster_title_html = f'<span style="font-weight: bold;">{most_important_words[0]}</span>, '
        cluster_title_html += ", ".join(list(most_important_words[1:])) + f" ({len(point_positions_per_cluster[cluster_id])}x, {avg_score * 100:.0f}%)"
        cluster_data.append({"id": cluster_id, "title": cluster_title, "title_html": cluster_title_html, "center": cluster_center,
                             "min_score": min_score, "max_score": max_score, "avg_score": avg_score,
                             "important_words": list(zip(words[most_important_words_idx[:5]], word_weights[most_important_words_idx[:5]]))})
    cluster_data = sorted(cluster_data, key=lambda cluster: cluster["avg_score"], reverse=True)
    timings.log("Tf-Idf for cluster titles")

    return cluster_data


LANGUAGE_IGNORE_WORDS = {
    'de': [
    "der",
    "die",
    "das",
    "für",
    "mit",
    "einer",
    "eine",
    "bei",
    "oder",
    "zur",
    "nach",
    "dem",
    "nicht",
    "aus",
    "auf",
    "von",
    "des",
    "im",
    "eigenen",
    "eigene",
    "eigener",
    "eines",
    "den",
    "als",
    "aller",
    "zu",
    "dass",
    "ist",
    "für",
    "zum",
    "werden",
    "wird",
    "durch",
  ],
}
