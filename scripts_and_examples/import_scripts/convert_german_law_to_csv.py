import csv

from langchain.text_splitter import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Abschnitt"),
    ("##", "Titel"),
    ("###", "Paragraph"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

splits = splitter.split_text(open("scripts_and_examples/sgb_as_markdown.md", "r").read())

csv_writer = csv.writer(open("scripts_and_examples/sgb_as_csv.csv", "w"))
csv_writer.writerow(["title", "subtitle", "text", "link"])

for split in splits:
    if not split.metadata.get('Paragraph'):
        continue
    title = f"{split.metadata.get('Paragraph')}"
    subtitle = f"{split.metadata.get('Titel')}"
    text = split.page_content
    # skip if text doesn't contain any letters
    if not any(c.isalpha() for c in text):
        continue
    csv_writer.writerow([title, subtitle, text, ""])
