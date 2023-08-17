import time
from collections import defaultdict

import gensim
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from utils.tokenizer import tokenize


class TfidfEmbeddingVectorizer(object):
    def __init__(self, word2vec, dim, sublinear_tf=False):
        self.word2vec = word2vec
        self.word2weight = None
        self.dim = dim
        self.sublinear_tf = sublinear_tf

    def fit(self, X):
        tfidf = TfidfVectorizer(analyzer=lambda x: x, sublinear_tf=self.sublinear_tf)
        tfidf.fit(X)
        # if a word was never seen - it must be at least as infrequent
        # as any of the known words - so the default idf is the max of
        # known idf's
        max_idf = max(tfidf.idf_)

        t1 = time.time()
        # TODO: this is slow, about 3s for 2k abstracts corpus (-> 20k unique words?)
        self.word2weight = defaultdict(
            lambda: max_idf, [(w, tfidf.idf_[i]) for w, i in tfidf.vocabulary_.items()]
        )
        print(f"tf idf vectorizer word2weight preproc: {time.time() - t1:.2}s")

        return self

    def transform(self, text):
        words = tokenize(text)
        return np.mean(
                    [
                        self.word2vec[w] * self.word2weight[w]
                        for w in words
                        if w in self.word2vec
                    ]
                    or [np.zeros(self.dim)],
                    axis=0,
                )


class GensimW2VVectorizer():

    def __init__(self) -> None:
        self.gensim_w2v_model = None

    def _w2v_iter_heuristic(self, nrows):
        def model(x, k, b):
            return k * np.log(x + 1) + b

        good_coefs = [-33.3979472, 307.3030023]
        # minimal_coefs = [-17.04255579, 160.19563678]
        n = model(nrows, *good_coefs)
        n = np.clip(n, 3, 120)
        return int(n)

    def prepare(self, corpus: list[str]):
        # copied from AbsClust:

        t8 = time.time()

        sentences = []
        for abstract in corpus:
            for sentence in abstract.split(". "):
                sentences.append(tokenize(sentence))

        emb_dim = 256
        window_size = 7
        n_epochs = self._w2v_iter_heuristic(len(corpus))
        n_workers = 8
        t9 = time.time()
        print(f"gensim model preparation: {t9 - t8:.2f}s, abstract count {len(corpus)}, sentence count {len(sentences)}, n_epochs {n_epochs}, n_workers {n_workers}")

        self.gensim_w2v_model = gensim.models.Word2Vec(
            sentences,
            vector_size=emb_dim,
            window=window_size,
            epochs=n_epochs,
            min_alpha=1e-5,
            workers=n_workers,
            compute_loss=True,
            sg=0,
        )
        t10 = time.time()
        print(f"gensim model training: {t10 - t9:.2f}s")

        self.w2v_dict = dict(zip(self.gensim_w2v_model.wv.index_to_key, self.gensim_w2v_model.wv.vectors))

        sublinear_tf = False
        self.tev = TfidfEmbeddingVectorizer(
            self.w2v_dict, dim=emb_dim, sublinear_tf=sublinear_tf
        )
        # to calculate tf-idfs we want list (abstracts) of lists words
        # i.e. we flatten over the sentence axis
        self.tev.fit([tokenize(abstract) for abstract in corpus])
        t11 = time.time()

        print(f"TfidfEmbeddingVectorizer training: {t11 - t10:.2f}s")


    def get_embedding(self, text):
        vector = self.tev.transform(text)
        return vector
