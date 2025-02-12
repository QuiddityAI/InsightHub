import re
import string

import spacy


class SpacyTokenizer:
    def __init__(self) -> None:
        self.preproc = "spacy"

        if self.preproc == "spacy":
            print("Using SpaCy for preprocessing...")
            self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
            self.nlp.add_pipe("sentencizer")
        else:
            raise ValueError("Preproc must be 'spacy' or 'nltk'")

        self.translation = str.maketrans("", "", string.punctuation)

    @staticmethod
    def correctPluralABB(s):
        if re.search(r"([A-Z]+?)(s\b)", s):
            return s[:-1]
        return s

    def removePunct(self, s):
        return s.translate(self.translation)

    @staticmethod
    def correctFirstlet(s):
        if s[0].isupper() and s[1:].islower():
            return s.lower()
        return s

    def normalizeWord(self, s):
        s = self.correctFirstlet(s)
        s = self.correctPluralABB(s)
        s = self.removePunct(s)
        return s

    def tokenize(self, text: str) -> list[str]:
        words = []
        tokens = self.nlp(text)
        for item in tokens:
            if not any([item.is_stop, item.is_punct, item.is_digit, item.is_space, item.__len__() <= 2]):
                words.append(self.normalizeWord(item.lemma_))
        return words
