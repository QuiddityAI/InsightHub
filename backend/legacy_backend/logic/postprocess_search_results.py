import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..utils.regex_tokenizer import tokenize

words_ignored_for_highlighting = ("on", "in", "using", "with", "the", "a", "of")


def enrich_search_results(search_results: list[object], query: str):
    tf_idf_corpus = [item["title"] + " " + item["abstract"] for item in search_results]

    # highlight TF-IDF words:
    vectorizer = TfidfVectorizer(analyzer=tokenize, max_df=0.7)
    tf_idf_matrix = vectorizer.fit_transform(tf_idf_corpus)
    # note: tf_idf_matrix is not a numpy array but a scipy sparse array
    vocabulary = vectorizer.get_feature_names_out()

    for i, item in enumerate(search_results):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[i].toarray()[0])
        most_important_words = list(vocabulary[sort_indexes_of_important_words[-5:]][::-1])
        item["most_important_words"] = most_important_words

        words_to_highlight = query.split(" ") + most_important_words
        important_words_regex = re.compile(
            f"\\b({'|'.join(re.escape(word) for word in words_to_highlight if word not in words_ignored_for_highlighting)})\\b",
            flags=re.IGNORECASE,
        )

        item["abstract"] = item["abstract"].replace("\n", "<br>")
        replacement = '<span class="font-bold">\\1</span>'
        item["title_enriched"] = important_words_regex.sub(replacement, item["title"])
        item["abstract_enriched"] = important_words_regex.sub(replacement, item["abstract"])

    return search_results
