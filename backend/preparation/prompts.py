
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