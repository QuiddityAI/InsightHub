
import re
from collections import defaultdict

academic_ignore_words = ["abstract", "figure", "cm", "mm", "kg", "μm", "kg-1", "g-1", "wt%", "db", "kpa", "mah"]
english_ignore_words = ["with", "is", "were", "in", "the", "a", "an", "of", "this", "and", "for", "we"]
ignore_words = set(academic_ignore_words + english_ignore_words)
html_tag_regex = re.compile(r"<.{1,8}?>(.{1,100}?)</.{1,8}?>", re.IGNORECASE)
latex_math_env_regex = re.compile(r"\$.{1,100}?\$", re.IGNORECASE)
word_split_regex = re.compile(r'[\s/]')
is_number_like_regex = re.compile(r"^[0-9.,-]+$")
is_plural_abbreviation_regex = re.compile(r"([A-Z]+?)(s\b)")

# from AbsClust:
def correct_plural_abbreviation(word):
    """corrects abbreviations in plural, e.g.
    ABBs -> ABB"""
    if is_plural_abbreviation_regex.match(word):
        return word[:-1]
    return word

def correct_first_letter(word):
    """corrects first letter, e.g. Word -> word
    use this instead of .lower to maintain abbreviations
    """
    if word[0].isupper() and word[1:].islower():
        return word.lower()
    return word

def tokenize(text, context_specific_ignore_words=set(), use_lower_case=True):
    # this method is called very often and a performance bottleneck
    # -> check criteria with most likely first and return early
    words = []
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("<sub>2</sub>", "₂")
    text = text.replace("<sub>3</sub>", "₃")
    text = text.replace("<sub>x</sub>", "ₓ")

    text = html_tag_regex.sub(r"\1", text)
    text = latex_math_env_regex.sub(r"", text)
    raw_words = word_split_regex.split(text)
    for word in raw_words:
        word = word.strip().strip("()[]{}<>'\".,;")
        if len(word) <= 1:
            continue
        word_lower = word.lower()
        if word_lower in ignore_words:
            continue
        if word_lower in context_specific_ignore_words:
            continue
        if is_number_like_regex.match(word):
            continue
        if word.startswith("www.") or word.startswith("http"):
            continue
        if '"' in word:  # for artifacts like 'xmlns:mml="http:'
            continue
        # TODO: strip accents?
        if len(words) >= 1 and words[-1] == word:
            continue
        word = correct_plural_abbreviation(word)
        if use_lower_case:
            word = correct_first_letter(word)
        words.append(word)

    return words


abstract = """
Abstract Direct printing of functional inks is critical for applications in diverse areas including electrochemical energy storage, smart electronics and healthcare. However, the available printable ink formulations are far from ideal. Either surfactants/additives are typically involved or the ink concentration is low, which add complexity to the manufacturing and compromises the printing resolution. Here, we demonstrate two types of two-dimensional titanium carbide (Ti 3 C 2 T x ) MXene inks, aqueous and organic in the absence of any additive or binary-solvent systems, for extrusion printing and inkjet printing, respectively. We show examples of all-MXene-printed structures, such as micro-supercapacitors, conductive tracks and ohmic resistors on untreated plastic and paper substrates, with high printing resolution and spatial uniformity. The volumetric capacitance and energy density of the all-MXene-printed micro-supercapacitors are orders of magnitude greater than existing inkjet/extrusion-printed active materials. The versatile direct-ink-printing technique highlights the promise of additive-free MXene inks for scalable fabrication of easy-to-integrate components of printable electronics.
"""

print(f"len(abstract): {len(abstract)}")

tokenized = tokenize(abstract)

print(f"len(''.join(tokenized)): {len(''.join(tokenized))}")

word_counts = defaultdict(int)
for word in tokenized:
    word_counts[word] += 1

print(f"word_counts: {word_counts}")

compressed = "|".join(f"{count}:{word}" if count > 1 else word for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True))

print(f"compressed: {compressed}")
print(f"len(compressed): {len(compressed)}")


"""
Results:

25% space reduction when tokenizing the abstract

almost no further reduction when compressing the tokenized abstract as a count of words

"""

