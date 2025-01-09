from collections import defaultdict

folder_summary_prompt_en = """
Summarize the content of a folder in one to two short sentences.
If the information is not enough, state that. Don't repeat the name of the folder.

This is known about the folder:
{{ context }}
"""
folder_summary_prompt_de = """
Fassen Sie den Inhalt eines Ordners in einem bis zwei kurzen Sätzen zusammen.
Wenn die Informationen nicht ausreichen, geben Sie dies an. Wiederholen Sie nicht den Namen des Ordners.

Dies ist über den Ordner bekannt:
{{ context }}
"""
folder_summary_prompt = defaultdict(lambda: folder_summary_prompt_en)
folder_summary_prompt["de"] = folder_summary_prompt_de

