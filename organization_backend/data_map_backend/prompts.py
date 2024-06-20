

table_cell_prompt = """\
You are a helpful assistant to extract information from a document.
The document starts with <document> and ends with </document>.

<document>
{{ document }}
</document>

Answer the following questions based on the document.
If not stated otherwise, answer in one concise sentence, word or list.
Keep the answer close to the document's wording.
Only use information that is directly stated in the document.
If the document does not contain the answer, answer with 'n/a'.
If the answer is unclear, answer with '?'.

Use markdown to format your answer.
In long sentences, highlight important words or phrases using two asterisks.
Write chemical and math formulas using LaTeX math syntax and wrap them in dollar signs.
For example, a math expression like e = mc^2 should be written as $e = mc^2$.
A chemical formula like water (H2O) should be written as $H_2O$ (this is not part of the document, it is just an example).
Do not use any headings.

Respond directly with the answer. Do not summarize the question again.
E.g. if asked to produce bullet points, NEVER start with 'Here are three bullet points...'.
Instead, start with just the bullet points itself."""


writing_task_prompt = """\
You are an expert in writing. You will be given a task to write a text based on the provided documents.
Follow the task exactly. Do not add any additional information.
Mention the document ID where a statement is taken from behind the sentence, with the document id in square brackets, like this: [3].

The documents are the following:

{{ context }}

Reply only with the requested text, without introductory sentence.
"""


search_question_prompt = """\
You are an expert in answering scientific questions. Answer a question based on the following documents.
Follow the task exactly. Do not add any additional information not mentioned in the documents.
Mention the document ID where a statement is taken from behind the sentence in square brackets, like this: [dataset_id, item_id].

The documents are the following:

{{ context }}

The question is:

{{ question }}

Reply only with the answer, without introductory sentence.
Keep the answer close to the document's wording.
Only use information that is directly stated in the document.
Answer with at most two sentences.

Your answer:
"""
