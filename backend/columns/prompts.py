from collections import defaultdict

column_name_prompt_en = """
The user has asked the following question / task:
"{{ expression }}"

What title best describes the results of this question / task?
The title should be one to three words long.
Answer only with the requested title, without anything else.
"""

column_name_prompt_de = """
Der Nutzer hat folgende Frage / Aufgabe gestellt:
"{{ expression }}"

Welche Überschrift beschreibt die Ergebnisse dieser Frage / Aufgabe am besten?
Der Titel sollte ein bis drei Wörter lang sein.
Antworte nur mit dem angeforderten Titel, ohne etwas anderes.
"""

column_name_prompt = defaultdict(lambda: column_name_prompt_en)
column_name_prompt["en"] = column_name_prompt_en
column_name_prompt["de"] = column_name_prompt_de

column_language_prompt = """
Return the two-letter language code (like 'de' or 'en') of the following question / expression.
Answer only with the language code, without anything else.

The title is: "{{ title }}"
The question / expression is: "{{ expression }}"
"""

item_relevance_prompt = """\
You are a helpful assistant for evaluating the relevance of a document based on a list of criteria.
The document starts with <document> and ends with </document>. Only the text between these tags is relevant.

<document>
{{ document }}
</document>

The criteria for relevance are:

<criteria>
{{ expression }}
</criteria>

Respond in the following JSON format:

[
    {
        "criteria": "Criterion...",
        "fulfilled": true / false,
        "reason": "Very brief explanation of why the criterion is fulfilled or not",
        "supporting_quote": "Short quote from the document matching the criterion"
    },
    {
        "criteria": "Criterion...",
        "fulfilled": true / false,
        "reason": "Very brief explanation of why the criterion is fulfilled or not",
        "supporting_quote": "Short quote from the document matching the criterion. Replace double quotes in the text with single quotes."
    },
    ...
]

The explanation should be in English. The quotes can be in the original language of the document.
Respond directly with the JSON array. Do not repeat the question.
"""

item_relevance_prompt_de = """\
Du bist ein hilfreicher Assistent, um die Relevanz eines Dokuments anhand einer Liste von Kriterien zu bewerten.
Das Dokument beginnt mit <document> und endet mit </document>. Nur der Text zwischen diesen Tags ist relevant.

<document>
{{ document }}
</document>

Die Kriterien für die Relevanz sind:

<criteria>
{{ expression }}
</criteria>

Antworte in folgendem JSON-Format:
[
    {
        "criteria": "Kriterium...",
        "fulfilled": true / false,
        "reason": "Sehr kurze Begründung, warum das Kriterium erfüllt oder nicht erfüllt ist",
        "supporting_quote": "Kurzes Zitat aus dem Dokument passend zum Kriterium"
    },
    {
        "criteria": "Kriterium...",
        "fulfilled": true / false,
        "reason": "Sehr kurze Begründung, warum das Kriterium erfüllt oder nicht erfüllt ist",
        "supporting_quote": "Kurzes Zitat aus dem Dokument passend zum Kriterium. Ersetze doppelte Anführungszeichen im Text durch einfache Anführungszeichen."
    },
    ...
]

Die Begründung soll deutschsprachig sein. Die Zitate können in der Originalsprache des Dokuments sein.
Antworte direkt mit dem JSON-Array. Wiederhole nicht die Frage.
"""
