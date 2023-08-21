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

ignore_words = ["abstract", "figure", "cm", "mm", "kg", "μm", "kg-1", "g-1", "wt%", "db", "kpa", "mah"]
html_tag_regex = re.compile(r"<.{1,8}?>(.{1,100}?)</.{1,8}?>", re.IGNORECASE)
latex_math_env_regex = re.compile(r"\$.{1,100}?\$", re.IGNORECASE)

# from AbsClust:
def correct_plural_abbreviation(s):
    """corrects abbreviations in plural, e.g.
    ABBs -> ABB"""
    if re.search(r"([A-Z]+?)(s\b)", s):
        return s[:-1]
    return s

def correct_first_letter(s):
    """corrects first letter, e.g. Word -> word
    use this instead of .lower to maintain abbreviations
    """
    if s[0].isupper() and s[1:].islower():
        return s.lower()
    return s

def tokenize(text):
    words = []
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("<sub>2</sub>", "₂")
    text = text.replace("<sub>3</sub>", "₃")
    text = text.replace("<sub>x</sub>", "ₓ")

    text = html_tag_regex.sub(r"\1", text)
    text = latex_math_env_regex.sub(r"", text)
    raw_words = re.split(r'[\s/]', text)
    for word in raw_words:
        word = word.strip().strip("()[]{}<>'\".,;")
        if len(word) <= 1:
            continue
        if word.replace("-", "").replace(".", "").replace(",", "").isnumeric():
            continue
        if word.startswith("www.") or word.startswith("http"):
            continue
        if '"' in word:  # for artifacts like 'xmlns:mml="http:'
            continue
        # TODO: strip accents?
        word = correct_plural_abbreviation(word)
        word = correct_first_letter(word)
        if word.lower() not in ignore_words:
            words.append(word)

    return words


if __name__ == "__main__":
    for line in examples_of_scientific_texts.splitlines():
        print(" | ".join(tokenize(line)))
    print(" | ".join(tokenize(examples_of_scientific_texts)))

    from utils.spacy_tokenizer import SpacyTokenizer
    tf_idf_helper = SpacyTokenizer()
    for line in examples_of_scientific_texts.splitlines():
        print(" | ".join(tf_idf_helper.tokenize(line)))
