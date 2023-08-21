from functools import lru_cache
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug import serving

from utils.collect_timings import Timings

from logic.postprocess_search_results import enrich_search_results
from logic.mapping_task import get_or_create_mapping_task, get_mapping_task_results, get_map_details, get_document_details, get_search_results_for_list


# --- Flask set up: ---

app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# exclude polling endpoints from logs (see https://stackoverflow.com/a/57413338):
parent_log_request = serving.WSGIRequestHandler.log_request

def log_request(self, *args, **kwargs):
    if self.path == '/api/map/result':
        return

    parent_log_request(self, *args, **kwargs)

serving.WSGIRequestHandler.log_request = log_request


# --- Routes: ---

@app.route('/api/query', methods=['POST'])
def query():
    # turn params into string to make it cachable (aka hashable):
    params_str = json.dumps(request.json, indent=2)
    print(params_str)
    return _query(params_str)


@lru_cache()
def _query(params_str):
    params = json.loads(params_str)
    query = params.get("query")
    if not query:
        return "query parameter is missing", 400

    timings = Timings()

    # TODO: currently only first page is returned
    search_results = get_search_results_for_list(query.split(" OR "), limit=params.get("result_list_items_per_page", 10))
    timings.log("database query")

    search_results = enrich_search_results(search_results, query)
    timings.log("enriching results")

    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
    }
    return jsonify(result)


@app.route('/api/map', methods=['POST'])
def get_or_create_map_task():
    params = request.json
    query = params.get("query")
    if not query:
        return "query parameter is missing", 400

    task_id = get_or_create_mapping_task(params)

    return jsonify({"task_id": task_id})


@app.route('/api/map/result', methods=['POST'])
def retrive_mapping_results():
    task_id = request.json.get("task_id")
    result = get_mapping_task_results(task_id)

    if result is None:
        return "task_id not found", 404

    return result


@app.route('/api/map/details', methods=['POST'])
def retrieve_map_details():
    task_id = request.json.get("task_id")
    result = get_map_details(task_id)

    if result is None:
        return "task_id not found", 404

    return result


@app.route('/api/document/details', methods=['POST'])
def retrieve_document_details():
    task_id = request.json.get("task_id")
    index = request.json.get("index")
    result = get_document_details(task_id, index)

    if result is None:
        return "task_id or index not found", 404

    return result


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55123', debug=True)
