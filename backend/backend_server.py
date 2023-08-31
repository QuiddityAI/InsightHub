from functools import lru_cache
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug import serving

from utils.collect_timings import Timings
from utils.dotdict import DotDict
from utils.custom_json_encoder import CustomJSONEncoder

from logic.postprocess_search_results import enrich_search_results
from logic.mapping_task import get_or_create_mapping_task, get_mapping_task_results, get_map_details, get_document_details, get_search_results_for_list
from logic.insert_logic import insert_many, update_database_layout

from database_client.django_client import get_object_schema


# --- Flask set up: ---

app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# exclude polling endpoints from logs (see https://stackoverflow.com/a/57413338):
parent_log_request = serving.WSGIRequestHandler.log_request

def log_request(self, *args, **kwargs):
    if self.path == '/data_backend/map/result':
        return

    parent_log_request(self, *args, **kwargs)

serving.WSGIRequestHandler.log_request = log_request


# --- New Routes: ---

@app.route('/data_backend/update_database_layout', methods=['POST'])
def update_database_layout_route():
    # TODO: check auth
    params = DotDict(request.json) # type: ignore
    update_database_layout(params.schema_id)
    return "", 204


@app.route('/data_backend/insert_many_sync', methods=['POST'])
def insert_many_sync_route():
    # TODO: check auth
    params = DotDict(request.json) # type: ignore
    insert_many(params.schema_id, params.elements)
    return "", 204


@app.route('/data_backend/search_list_result', methods=['POST'])
def get_search_list_result():
    # turn params into string to make it cachable (aka hashable):
    params_str = json.dumps(request.json, indent=2)
    print(params_str)
    return _get_search_list_result(params_str)


#@lru_cache()
def _get_search_list_result(params_str):
    timings = Timings()

    params = json.loads(params_str)
    query = params.get("query")
    limit_per_page = params.get("result_list_items_per_page")
    page = params.get("page")
    schema_id = params.get("schema_id")
    vector_field = params.get("vector_field")
    if not all([query, limit_per_page, page is not None, schema_id, vector_field]):
        return "a parameter is missing", 400

    # TODO: currently only first page is returned
    schema = get_object_schema(schema_id)
    list_rendering = json.loads(schema.result_list_rendering)
    timings.log("preparation")

    search_results = get_search_results_for_list(schema, vector_field, query.split(" OR "), list_rendering['required_fields'], limit=limit_per_page, page=page)
    timings.log("database query")

    # search_results = enrich_search_results(search_results, query)
    # timings.log("enriching results")
    # -> replaced by context dependent generator (for important words per abstract and highlighting of words)

    print(json.dumps(search_results[0], indent=4, cls=CustomJSONEncoder))

    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
        "rendering": list_rendering,
    }
    response = app.response_class(
        response=json.dumps(result, cls=CustomJSONEncoder),
        mimetype='application/json'
    )
    return response


# --- Old Routes: ---


@app.route('/data_backend/map', methods=['POST'])
def get_or_create_map_task():
    params = request.json or {}
    query = params.get("query")
    if not query:
        return "query parameter is missing", 400

    task_id = get_or_create_mapping_task(params)

    return jsonify({"task_id": task_id})


@app.route('/data_backend/map/result', methods=['POST'])
def retrive_mapping_results():
    params = request.json or {}
    task_id = params.get("task_id")
    result = get_mapping_task_results(task_id)

    if result is None:
        return "task_id not found", 404

    return result


@app.route('/data_backend/map/details', methods=['POST'])
def retrieve_map_details():
    params = request.json or {}
    task_id = params.get("task_id")
    result = get_map_details(task_id)

    if result is None:
        return "task_id not found", 404

    return result


@app.route('/data_backend/document/details', methods=['POST'])
def retrieve_document_details():
    params = request.json or {}
    task_id = params.get("task_id")
    index = params.get("index")
    result = get_document_details(task_id, index)

    if result is None:
        return "task_id or index not found", 404

    return result


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=55123, debug=True)
