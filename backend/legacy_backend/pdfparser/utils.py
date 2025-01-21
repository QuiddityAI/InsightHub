import re
from itertools import islice


def split_every(iterable, n):
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))


def remove_hyphenation(text):
    pattern = r"(\w+)\-\s*\n\s*(\w+)"
    cleaned_text = re.sub(pattern, r"\1\2", text)
    return cleaned_text.replace("\n", "")
