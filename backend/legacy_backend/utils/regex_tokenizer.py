import re

examples_of_scientific_texts = """
2D MXene
Abstract

2D materials' membranes. Two-dimensional Ti3C2Tx MXene nanosheets.
For example this (NiFe2O4/MXene); and here NiFe2O4. (EMW)
(RLmin =  − 5.03 dB)
(e.g., 3D printing and stamping) μM
−50 to 150 °C.
B/KNO3 cylinder
with 1 wt% MXene of 0.31 W m−1 K−1,
range of 3.44–18 GHz
            <sub>3</sub> H<sub>2</sub>O
            C
            <sub>2</sub>
            C Mxene quantum dots (QDs)
Lithium–Oxygen Batteries
high-performance Ag3PO4/TiO2@C composite
3. M. Naguib, V. N. Mochalin, M. W. Barsoum, Y. Gogotsi, 25th Anniversary Article
                  26, 992-1005 (2014).
Figure 1
            <i>
              <sub>x</sub>
            </i>
<mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML"><mml:mrow><mml:msub><mml:mi>Ti</mml:mi><mml:mn>2</mml:mn></mml:msub><mml:mi mathvariant="normal">C</mml:mi></mml:mrow></mml:math>
<p>Ab</p>
$5.5~\mu \text{s}$
of the MXene ${\mathrm{Sc}}_{2}\mathrm{C}$, which has
<scp>3D</scp>
a novel CdS/MoO2@Mo2C-MXene photocatalyst
"""

academic_ignore_words = ["abstract", "figure", "cm", "mm", "kg", "μm", "kg-1", "g-1", "wt%", "db", "kpa", "mah"]
english_ignore_words = ["with", "is", "were", "in", "the", "a", "an", "of", "this", "and", "for", "we"]
ignore_words = set(academic_ignore_words + english_ignore_words)
html_tag_regex = re.compile(r"<.{1,8}?>(.{1,100}?)</.{1,8}?>", re.IGNORECASE)
latex_math_env_regex = re.compile(r"\$.{1,100}?\$", re.IGNORECASE)
word_split_regex = re.compile(r"[\s/]")
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


if __name__ == "__main__":
    for line in examples_of_scientific_texts.splitlines():
        print(" | ".join(tokenize(line)))
    print(" | ".join(tokenize(examples_of_scientific_texts)))
