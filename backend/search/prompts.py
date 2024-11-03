from collections import defaultdict


search_query_prompt_en = """
Write a search query that you would use to find the following information.
The query should be short and concise.
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
Die Anfrage sollte kurz und prägnant sein.
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

