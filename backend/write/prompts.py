from collections import defaultdict

writing_task_prompt_without_items_en = """\
You are a helpful assistant.

{{ context }}
"""
writing_task_prompt_without_items: dict[str, str] = defaultdict(lambda: writing_task_prompt_without_items_en)
