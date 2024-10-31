column_name_prompt = """
Return a very short name for the following question / expression.
The name should be at most three words long.
The name should be in the same language as the question / expression.
Answer only with the requested name, without anything else.

The question / expression is: {{ expression }}
"""
