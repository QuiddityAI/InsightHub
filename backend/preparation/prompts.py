
item_relevancy_prompt = """\
You are an expert in assessing the relevance of a document to a given question.

The user had the following question or search query:

    "{{ question }}"

Reply using json with the following format:
{
    "explanation": "Explain why the document is relevant or not relevant to the question in less than 10 words.",
    "decision": true if the document is relevant, false if it is not relevant
}
Reply only with the requested json, without introductory sentence.
"""