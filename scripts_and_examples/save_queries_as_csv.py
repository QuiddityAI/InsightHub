# to be used in manage.py shell_plus console:
import json

a = SearchHistoryItem.objects.filter(parameters__search__search_type="external_input")

t = "query, filters, total_matches\n"
for e in a:
    filters = json.dumps(e.parameters["search"]["filters"]).replace('"', '\\"')
    t += f'"{e.parameters["search"]["all_field_query"]}", "{filters}", {e.total_matches or -1}\n'

open("queries.txt", "w").write(t)
