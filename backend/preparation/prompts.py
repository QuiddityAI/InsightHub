
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

# writing_task_prompt = """\
# You are an expert in writing a summary of a document.

# Answer the following question based on the provided information:

#         "{{ question }}"

# Answer the question in less than 100 words.
# Use bullet points if necessary.

# """