column_name_prompt = """
Return a very short title for the result of following question / expression.
The title should be at most three words long.
The title should be in the same language as the question / expression.
Answer only with the requested title, without anything else.

The question / expression is: {{ expression }}
"""

column_language_prompt = """
Return the two-letter language code (like 'de' or 'en') of the following question / expression.
Answer only with the language code, without anything else.

The title is: {{ title }}
The question / expression is: {{ expression }}
"""
