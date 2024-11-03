from collections import defaultdict

column_name_prompt_en = """
Return a very short title for the result of following question / expression.
The title should be at most three words long.
Answer only with the requested title, without anything else.

The question / task is: {{ expression }}
"""

column_name_prompt_de = """
Gib einen sehr kurzen Titel für das Ergebnis der folgenden Frage / des folgenden Ausdrucks an.
Der Titel sollte maximal drei Wörter lang sein.
Antworte nur mit dem angeforderten Titel, ohne etwas anderes.

Die Frage / die Aufgabe ist: {{ expression }}
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

item_relevancy_prompt = """\
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
        "supporting_quote": "Short quote from the document matching the criterion"
    },
    ...
]

The explanation should be in English. The quotes can be in the original language of the document.
Respond directly with the JSON array. Do not repeat the question.
"""

item_relevancy_prompt_de = """\
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
        "supporting_quote": "Kurzes Zitat aus dem Dokument passend zum Kriterium"
    },
    ...
]

Die Begründung soll deutschsprachig sein. Die Zitate können in der Originalsprache des Dokuments sein.
Antworte direkt mit dem JSON-Array. Wiederhole die nicht die Frage.
"""
