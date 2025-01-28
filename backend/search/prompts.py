from collections import defaultdict

search_query_prompt_en = """
Write a search query that you would use to find the following information.
If the user input is already a search query, write the same query.

Examples:
User input: "What is the capital of France?"
Search query: "capital of France"

User input: "a technical drawing of a car in a PDF file"
Search query: "technical drawing car PDF"

User input: "a list of the most popular programming languages"
Search query: "most popular programming languages"

User input: "histopathology cell segmentation algorithm"
Search query: "histopathology cell segmentation algorithm"

The user input is: {{ user_input }}
Return just the search query. Do not repeat the task.
"""

search_query_prompt_de = """
Schreibe eine Suchanfrage, die du verwenden würdest, um die folgende Information zu finden.
Falls die Benutzereingabe bereits eine Suchanfrage ist, verwende dieselbe Anfrage.

Beispiele:
Benutzereingabe: "Was ist die Hauptstadt von Frankreich?"
Suchanfrage: "Hauptstadt von Frankreich"

Benutzereingabe: "eine technische Zeichnung eines Autos in einer PDF-Datei"
Suchanfrage: "technische Zeichnung Auto PDF"

Benutzereingabe: "eine Liste der beliebtesten Programmiersprachen"
Suchanfrage: "beliebteste Programmiersprachen"

Benutzereingabe: "Histopathologie Zellsegmentierungsalgorithmus"
Suchanfrage: "Histopathologie Zellsegmentierungsalgorithmus"

Die Benutzereingabe ist: {{ user_input }}
Gib nur die Suchanfrage zurück. Wiederhole nicht die Aufgabe.
"""

search_query_prompt: defaultdict[str, str] = defaultdict(lambda: search_query_prompt_en)
search_query_prompt["en"] = search_query_prompt_en
search_query_prompt["de"] = search_query_prompt_de

# Note: this prompt is just a template for the Dataset settings and is not direclty used
filter_detection_prompt_en = """
# language: en
Return an array of filters extracted from a given natural language search query.

The filters should be in the following JSON array format:
[
    {
        "field": "field_name",
        "operator": one of "contains", "does_not_contain", "is", "is_not", "gt", "lt", "gte", "lte",
        "value": "value"
    },
    ...
]

Rules:
- If a query mentions a specific year or year range, filter by that year:
[
    {
        "field": "publication_year",
        "operator": "gt" or "lt" or "gte" or "lte" or "is" or "is_not",
        "value": "year"
    }
]
- If a query mentions a specific author, filter by that author.
[
    {
        "field": "authors",
        "operator": "contains" or "does_not_contain",
        "value": "author_name"
    }
]
- If a query says a specific keyword should not be present, filter by that keyword.
[
    {
        "field": "abstract",
        "operator": "does_not_contain",
        "value": "keyword"
    }
]

Only include filters if one or more rules apply.
If no rules apply, return an empty array.
Only return filters if you are confident that they are correct.

Examples:
Search query: "papers that are not about graphene"
Filters:
[
    {
        "field": "abstract",
        "operator": "does_not_contain",
        "value": "graphene"
    }
]

Search query: "mxene photocalytic papers after the year 2015"
Filters:
[
    {
        "field": "publication_year",
        "operator": "gt",
        "value": "2015"
    }
]

Search query: "papers about the applications of graphene"
Filters: []

Search query: "How can the material Mxene be used for solar cells?"
Filters: []

Search query: "What are recent advances in the field of nanotechnology?"
Filters: []

The search query is: {{ user_input }}

Return just the filters as a JSON array. Do not repeat the task.
"""

approve_using_comparison_prompt_en = """
Compare the following documents and select those that should be used to answer a question.
It is possible that no document is relevant. It is also possible that multiple or all documents are relevant.
If a document is relevant but another is more relevant for the same information, select only the more relevant document.
Select only as many documents as are necessary to answer the question.
If multiple documents are very similar or identical, select only the newest one (or the first one, if this cannot be determined).
Only the metadata of each document will be displayed, not the full content.
If a relevance justification is provided ("Relevance: reason"), trust this justification.

The question/user input is: "{{ user_input }}"

The documents are:

{{ documents }}

Specify the documents that should be used to answer the question.
Provide a very brief justification for each document selected (e.g., because it is more relevant than another document).
Respond directly in the following JSON format (without any additional characters):

[
 {
    "item_id": item_id,
    "reason": "reason"
 },
    ...
]
"""

approve_using_comparison_prompt_de = """
Vergleiche die folgenden Dokumente und wähle die aus, die zur Beantwortung einer Frage genutzt werden sollen.
Es kann sein, dass kein Dokument relevant ist. Es können auch mehrere oder alle Dokumente relevant sein.
Wenn ein Dokument relevant ist, ein anderes aber noch relevanter für die selben Informationen, wähle nur das relevantere Dokument.
Wähle nur so viele Dokumente aus, wie nötig sind, um die Frage zu beantworten.
Wenn mehrere Dokumente sehr ähnlich oder gleich sind, wähle nur das neuste aus (oder das erste, falls das nicht feststellbar ist).
Für jedes Dokument werden nur die Metadaten und nicht der gesamte Inhalt angezeigt.
Wenn eine Relevanzbegründung angegeben ist ("Relevance: reason"), vertraue dieser Begründung.

Die Frage / Benutzereingabe lautet: "{{ user_input }}"

Die Dokumente sind:

{{ documents }}

Gib die Dokumente an, die zur Beantwortung der Frage genutzt werden sollten.
Gib jeweils eine sehr kurze Begründung an, warum das Dokument ausgewählt wurde (z.B. weil es relevanter als ein anderes Dokument ist).
Antworte direkt in folgendem JSON-Format (ohne jegliche zusätzliche Zeichen):

[
 {
    "item_id": item_id,
    "reason": "reason"
 },
    ...
]
"""

approve_using_comparison_prompt: defaultdict[str, str] = defaultdict(lambda: approve_using_comparison_prompt_en)
approve_using_comparison_prompt["en"] = approve_using_comparison_prompt_en
approve_using_comparison_prompt["de"] = approve_using_comparison_prompt_de


notification_email_en = """\
Hello,

there were items added to your collection "{{ collection_name }}":

{{ new_items }}

You can view the collection here: {{ collection_url }}

--

This email was sent by Quiddity.
"""

notification_email_de = """\
Hallo,

es wurden Elemente zu deiner Sammlung hinzugefügt "{{ collection_name }}":

{{ new_items }}

Du kannst die Sammlung hier ansehen: {{ collection_url }}

--

Diese E-Mail wurde von Quiddity gesendet.
"""

notification_email: defaultdict[str, str] = defaultdict(lambda: notification_email_en)
notification_email["en"] = notification_email_en
notification_email["de"] = notification_email_de
