from collections import defaultdict


query_language_prompt = """
Return the two-letter language code (like 'de' or 'en') of the following query.
Answer only with the language code, without anything else.

The query is: {{ query }}
"""

criteria_prompt_en = """
For a given query, write a list of criteria that potential search results have to fulfill.

Examples:
Query: "What is the capital of France?"
Criteria:
- mentions the capital of France

Query: "a technical drawing of a car in a PDF file"
Criteria:
- contains a technical drawing
- is about a car
- is a PDF file

Query: "a list of the most popular programming languages"
Criteria:
- contains a list
- names the most popular programming languages

The query is: "{{ query }}"

Return only the criteria as a list of bullet points. Do not repeat the task.
"""


criteria_prompt_de = """
Für eine gegebene Suchanfrage, schreibe eine Liste von Kriterien, die potenzielle Suchergebnisse erfüllen müssen.

Beispiele:
Anfrage: "Was ist die Hauptstadt von Frankreich?"
Kriterien:
- nennt die Hauptstadt von Frankreich

Anfrage: "eine technische Zeichnung eines Autos in einer PDF-Datei"
Kriterien:
- enthält eine technische Zeichnung
- handelt von einem Auto
- ist eine PDF-Datei

Anfrage: "eine Liste der beliebtesten Programmiersprachen"
Kriterien:
- enthält eine Liste
- nennt die beliebtesten Programmiersprachen

Die Suchanfrage ist: "{{ query }}"

Gib nur die Kriterien als Liste von Aufzählungspunkten zurück. Wiederhole die Aufgabe nicht.
"""

criteria_prompt: defaultdict[str, str] = defaultdict(lambda: criteria_prompt_en)
criteria_prompt['en'] = criteria_prompt_en
criteria_prompt['de'] = criteria_prompt_de
