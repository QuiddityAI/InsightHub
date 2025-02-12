from collections import defaultdict

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


notification_email_en = """\
## New items ➔ *{{ collection_name }}*:

---

{{ new_items }}

You can view the whole collection [here]({{ collection_url }}).

--

_This email was sent by Quiddity._
"""

notification_email_de = """\
## Neue Elemente ➔ *{{ collection_name }}*:

---

{{ new_items }}

Du kannst die gesammte Sammlung [hier]({{ collection_url }}) ansehen.

--

_Diese E-Mail wurde von Quiddity gesendet._
"""

notification_email: defaultdict[str, str] = defaultdict(lambda: notification_email_en)
notification_email["en"] = notification_email_en
notification_email["de"] = notification_email_de
