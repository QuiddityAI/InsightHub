column_name_prompt = """
Return a very short title for the result of following question / expression.
The title should be at most three words long.
The title should be in the same language as the question / expression.
Answer only with the requested title, without anything else.

The question / expression is: {{ expression }}
"""

column_language_prompt = """
Return the two-letter language code (like 'de' or 'en') of the following question / expression.
Answer only with the language code, without anything else.

The title is: {{ title }}
The question / expression is: {{ expression }}
"""

item_relevancy_prompt = """\
You are a helpful assistant to assess the relevance of a document to a question or search query.
The document starts with <document> and ends with </document>.

<document>
{{ document }}
</document>

Evaluate if and how the document is relevant to the following question or search query:

"{{ expression }}"

Answer with a JSON object in the following format:
{
    "document_type": "paper about a new algorithm",
    "relevant_content": "- key insight 1\\n- key insight 2\\n- key insight 3",
    "irrelevance_reasons": "- reason 1\\n- reason 2",
    "is_relevant": true,
    "relevance_score": 0.8,
}

The "document_type" field should contain the abstract type of the document, e.g. "paper about a new algorithm", "study comparing two methods", "website of a company", "report about a new discovery".
Do not repeat the title of the document or the query. Keep it under 10 words.

The "relevant_content" field should summarize the relevant parts of the document in three bullet points.
Highlight what makes this document special.
If the document is not relevant, leave this field empty.

The "irrelevance_reasons" field can contain up to three aspects of how the document is not relevant to the question or parts of it.
If all aspects are covered, leave this field empty.

For both "relevant_content" and "irrelevance_reasons":
Answer using very short bullet points in markdown format.
Each bullet point should be at most a few words or a short phrase.
You can highlight important words using two asterisks.
Write chemical and math formulas using LaTeX math syntax and wrap them in dollar signs.
For example, a math expression like e = mc^2 should be written as $e = mc^2$.
A chemical formula like water (H2O) should be written as $H_2O$ (this is not part of the document, it is just an example).

The "is_relevant" field should be true if the document is relevant to the question in general and false otherwise.

The "relevance_score" field should be a number between 0 and 1 indicating the relevance of the document to the question.
If the document is relevant to all aspects of the question, the score should be 1.
If it is relevant to only some aspects, the score should be 0.5. If it is not relevant at all, the score should be 0.

Respond directly with the JSON object. Do not summarize the question again.
"""

item_relevancy_prompt_de = """\
Du bist ein hilfreicher Assistent, um die Relevanz eines Dokuments für eine Frage oder Suchanfrage zu bewerten.
Das Dokument beginnt mit <document> und endet mit </document>.

<document>
{{ document }}
</document>

Bewerte, ob und wie das Dokument relevant für die folgende Frage oder Suchanfrage ist:

"{{ expression }}"

Antworte mit einem JSON-Objekt im folgenden Format:
{
    "document_type": "Paper über einen neuen Algorithmus",
    "relevant_content": "- wichtiger Punkt 1\\n- wichtiger Punkt 2\\n- wichtiger Punkt 3",
    "irrelevance_reasons": "- Grund 1\\n- Grund 2",
    "is_relevant": true,
    "relevance_score": 0.8,
}

Das Feld "document_type" sollte den abstrakten Typ des Dokuments enthalten, z.B. "Paper über einen neuen Algorithmus", "Studie zum Vergleich zweier Methoden", "Webseite eines Unternehmens", "Bericht über eine neue Entdeckung".
Wiederhole nicht den Titel des Dokuments oder die Suchanfrage. Halte es unter 10 Wörtern.

Das Feld "relevant_content" sollte die relevanten Teile des Dokuments in drei Aufzählungspunkten zusammenfassen.
Hebe hervor, was das Dokument besonders macht.
Wenn das Dokument nicht relevant ist, lasse dieses Feld leer.

Das Feld "irrelevance_reasons" kann bis zu drei Aspekte enthalten, warum das Dokument nicht relevant für die Frage oder Teile davon ist.
Wenn alle Aspekte abgedeckt sind, lasse dieses Feld leer.

Für "relevant_content" und "irrelevance_reasons":
Antworte mit sehr kurzen Aufzählungspunkten im Markdown-Format.
Jeder Aufzählungspunkt sollte höchstens aus wenigen Wörtern oder einer kurzen Phrase bestehen.
Du kannst wichtige Wörter mit zwei Sternchen hervorheben.
Schreibe chemische und mathematische Formeln im LaTeX-Mathematikformat und setze sie in Dollarzeichen.
Zum Beispiel sollte ein mathematischer Ausdruck wie e = mc^2 als $e = mc^2$ geschrieben werden.
Eine chemische Formel wie Wasser (H2O) sollte als $H_2O$ geschrieben werden (dies ist kein Teil des Dokuments, es ist nur ein Beispiel).

Der Inhalt der Felder soll in deutsche Sprache beantwortet werden.

Das Feld "is_relevant" sollte auf "true" gesetzt werden, wenn das Dokument im Allgemeinen relevant für die Frage ist, und auf "false" gesetzt werden, wenn dies nicht der Fall ist.

Das Feld "relevance_score" sollte eine Zahl zwischen 0 und 1 sein, die die Relevanz des Dokuments für die Frage angibt.
Wenn das Dokument in allen Aspekten relevant ist, sollte die Punktzahl 1 sein.
Wenn es nur teilweise relevant ist, sollte der Wert 0.5 betragen.
Wenn es überhaupt nicht relevant ist, sollte der Wert 0 sein.

Antworte direkt mit dem JSON-Objekt. Wiederhole die Frage nicht.
"""
