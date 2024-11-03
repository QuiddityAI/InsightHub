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
search_query_prompt['en'] = search_query_prompt_en
search_query_prompt['de'] = search_query_prompt_de

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
