

table_cell_prompt = """\
You are a helpful assistant to extract information from a document.
The document (also called item) starts with <document> and ends with </document>.

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

table_cell_prompt_de = """\
Du bist ein hilfreicher Assistent, der Informationen aus einem Dokument extrahiert.
Das Dokument beginnt mit <document> und endet mit </document>.

<document>
{{ document }}
</document>

Beantworte die folgenden Fragen basierend auf dem Dokument.
Falls nicht anders angegeben, antworte in einem knappen Satz, Wort oder einer Liste.
Halte die Antwort nahe am Wortlaut des Dokuments.
Nutze nur Informationen, die direkt im Dokument angegeben sind.
Falls die Antwort nicht im Dokument enthalten ist, antworte mit „n/a“.
Falls die Antwort unklar ist, antworte mit „?“.

Nutze Markdown, um deine Antwort zu formatieren.
Bei längeren Sätzen hebe wichtige Wörter oder Phrasen mit zwei Sternchen hervor.
Schreibe chemische und mathematische Formeln mit LaTeX-Syntax und setze sie in Dollarzeichen.
Zum Beispiel sollte eine mathematische Formel wie $e = mc^2$ geschrieben werden.
Eine chemische Formel wie Wasser (H2O) sollte als $H_2O$ geschrieben werden (dies ist kein Teil des Dokuments, nur ein Beispiel).

Antworte direkt mit der Antwort. Wiederhole die Frage nicht erneut.
Zum Beispiel, wenn du Stichpunkte geben sollst, beginne NIE mit „Hier sind drei Stichpunkte...“.
Stattdessen beginne direkt mit den Stichpunkten.
"""

writing_task_prompt = """\
You are an expert in writing. You will be given a task to write a text based on the provided documents.

Follow the task exactly. Only use information that is directly stated in the documents.
If the document does not contain the answer, state that.

Use markdown to format your text. Use bullet points and numbered lists where appropriate.
Highlight important phrases using two asterisks.

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

dataset_context = "The user can search in a big archive of documents. A document is relevant if it contains information that is directly useful for the user's search query."

item_relevancy_prompt = """\
You are an expert in assessing the relevance of a document to a given question.

Context:
{{ dataset_context }}


The document starts with <document> and ends with </document>.

<document>

{{ document }}

</document>


The user had the following question or search query:

    {{ question }}

Reply using json with the following format:
{
    "explanation": "Explain why the document is relevant or not relevant to the question in less than 10 words.",
    "decision": true if the document is relevant, false if it is not relevant
}
Reply only with the requested json, without introductory sentence.
"""