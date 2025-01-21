from collections import defaultdict


query_language_prompt = """
Return the two-letter language code (like 'de' or 'en') of the following query.
Answer only with the language code, without anything else.

The query is: {{ query }}
"""

criteria_prompt_en = """
For a given query, write a list of criteria that potential search results have to fulfill.
Only split the query into multiple parts if it is necessary to easily evaluate the criteria.
Do not add any additional criteria that are not included in the query.

Examples:
Query: "What is the capital of France?"
Criteria:
- mentions the capital of France

Query: "a technical drawing of a car in a PDF file"
Criteria:
- contains a technical drawing of a car
- is a PDF file

Query: "a list of the most popular programming languages of 2022"
Criteria:
- contains a list of the most popular programming languages
- refers to the year 2022

Query: "cost breakdown of facility XYZ for October 2014"
Criteria:
- is a project plan
- refers to facility XYZ
- refers to the month October 2014

Query: "recycling process for hard plastic"
Criteria:
- is about recycling processes for hard plastic

The query is: "{{ query }}"

Return only the criteria as a list of bullet points. Do not repeat the task.
"""


criteria_prompt_de = """
Für eine gegebene Suchanfrage, schreibe eine Liste von Kriterien, die potenzielle Suchergebnisse erfüllen müssen.
Teile die Anfrage nur in mehrere Teile auf, wenn es notwendig ist, um die Kriterien leicht zu bewerten.
Füge keine weiteren Kriterien hinzu, die nicht in der Anfrage enthalten sind.

Beispiele:
Anfrage: "Was ist die Hauptstadt von Frankreich?"
Kriterien:
- nennt die Hauptstadt von Frankreich

Anfrage: "eine technische Zeichnung eines Autos in einer PDF-Datei"
Kriterien:
- enthält eine technische Zeichnung eines Autos
- ist eine PDF-Datei

Anfrage: "eine Liste der beliebtesten Programmiersprachen von 2022"
Kriterien:
- enthält eine Liste der beliebtesten Programmiersprachen
- bezieht sich auf das Jahr 2022

Anfrage: "Kostenabrechnung der Anlage XYZ für Oktober 2014"
Kriterien:
- ist ein Projektplan
- bezieht sich auf die Anlage XYZ
- bezieht sich auf den Monat Oktober 2014

Anfrage: "Recyclingverfahren für Hartplastik"
Kriterien:
- handelt von Recyclingverfahren für Hartplastik

Die Suchanfrage ist: "{{ query }}"

Gib nur die Kriterien als Liste von Aufzählungspunkten zurück. Wiederhole die Aufgabe nicht.
"""

criteria_prompt: defaultdict[str, str] = defaultdict(lambda: criteria_prompt_en)
criteria_prompt["en"] = criteria_prompt_en
criteria_prompt["de"] = criteria_prompt_de
