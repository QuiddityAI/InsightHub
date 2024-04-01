import datetime
import json
import os
from copy import deepcopy
from threading import Thread

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug import serving
import cbor2

from utils.custom_json_encoder import CustomJSONEncoder, HumanReadableJSONEncoder
from utils.dotdict import DotDict

from logic.mapping_task import get_or_create_map, get_map_results
from logic.insert_logic import insert_many, update_database_layout, delete_dataset_content
from logic.search import get_search_results, get_search_results_for_stored_map, get_document_details_by_id, get_item_count, get_random_items, get_items_having_value_count
from logic.generate_missing_values import delete_field_content, generate_missing_values
from logic.thumbnail_atlas import THUMBNAIL_ATLAS_DIR
from logic.classifiers import get_retraining_status, start_retrain
from logic.upload_files import upload_files, UPLOADED_FILES_FOLDER

from database_client.django_client import add_stored_map


# --- Flask set up: ---

app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# exclude polling endpoints from logs (see https://stackoverflow.com/a/57413338):
parent_log_request = serving.WSGIRequestHandler.log_request

paths_excluded_from_logging = ['/data_backend/map/result',
                               '/data_backend/document/details_by_id',
                               '/health',
                               ]

def log_request(self, *args, **kwargs):
    if self.path in paths_excluded_from_logging or self.path.startswith("/data_backend/local_image/"):
        return

    parent_log_request(self, *args, **kwargs)

serving.WSGIRequestHandler.log_request = log_request


# --- New Routes: ---

# search needs:
#   input: text, image, document (if generator in same embd space avail.)
#   input: negative query (text, image, document) or direction e.g. for image as a word
#   where: vector fields (threshold algorithm (knee)), text fields (fix typo, synonyms etc.)
#   enrich results (only for map?, with neural search per text result etc.)
#   filter results (remove if not both vectors are similar to query etc.)
#   re-score algorithm (tokenizer, aggregation or generator)
#   near-duplicate removal or grouping
#   - How to handle negative queries?
# list only: rank fusion (based on new score, or alternating),
#   highlighting (tokenizer) (on-demand for map, means tf-idf corpus should be kept)
# long list search: updated with map features
# map needs:
#   input: existing vector or set of text fields for w2v
#   multiply with direction word (generator, w2v)
#   umap / t-SNE
#   hdbscan / custom clusterizer
#   cluster title (tf-idf, generative ai)
#   visual settings (color, size, etc.)

# user settings: fields to search, enrich?, map field(s), cluster size

# How to make it customizable and still offer default search and map for datasets?
# -> as currently, offer all settings in UI and select basic defaults based on dataset
# How to apply search and map settings to different datasets (with different field names etc.)?
# Dataset could have default set of vector and text search / map fields, but
# what if there should be two search / map settings for the same dataset?
# E.g. for products, search in title only or in reviews, map based on image or on reviews
# Should search and map settings be separated? Would map always use same search settings as list?
# map might be enriched much more, clustering might be done on different aspect (only image, not title)
# given 100 products all called "white t-shirt", search by title but map by image


@app.route('/health', methods=['GET'])
def health():
    return "", 200


@app.route('/data_backend/dataset/<int:dataset_id>/item_count', methods=['GET'])
def get_item_count_route(dataset_id: int):
    count = get_item_count(dataset_id)
    return jsonify({"count": count})


@app.route('/data_backend/dataset/<int:dataset_id>/<field>/items_having_value_count', methods=['GET'])
def get_items_having_value_count_route(dataset_id: int, field: str):
    count = get_items_having_value_count(dataset_id, field)
    return jsonify({"count": count})


@app.route('/data_backend/dataset/<int:dataset_id>/<field>/sub_items_having_value_count', methods=['GET'])
def get_sub_items_having_value_count_route(dataset_id: int, field: str):
    count = get_items_having_value_count(dataset_id, field, count_sub_items=True)
    return jsonify({"count": count})


@app.route('/data_backend/dataset/<int:dataset_id>/random_item', methods=['GET'])
def get_random_item_route(dataset_id: int):
    items = get_random_items(dataset_id, 1)
    item = items[0] if len(items) else {}
    response = app.response_class(
        response=json.dumps({"item": item}, cls=HumanReadableJSONEncoder),  # type: ignore
        mimetype='application/json'
    )
    return response


@app.route('/data_backend/update_database_layout', methods=['POST'])
def update_database_layout_route():
    # TODO: check auth
    params = DotDict(request.json) # type: ignore
    try:
        update_database_layout(params.dataset_id)
    except Exception as e:
        return repr(e), 500
    return "", 204


@app.route('/data_backend/insert_many_sync', methods=['POST'])
def insert_many_sync_route():
    # TODO: check auth
    params = DotDict(request.json) # type: ignore
    try:
        insert_many(params.dataset_id, params.elements)
    except Exception as e:
        return repr(e), 500
    return "", 204


@app.route('/data_backend/delete_field', methods=['POST'])
def delete_field_route():
    # TODO: check auth
    params = DotDict(request.json) # type: ignore
    delete_field_content(params.dataset_id, params.field_identifier)
    return "", 204


@app.route('/data_backend/generate_missing_values', methods=['POST'])
def generate_missing_values_route():
    # TODO: check auth
    params = DotDict(request.json) # type: ignore
    thread = Thread(target=generate_missing_values, args=(params.dataset_id, params.field_identifier))
    thread.start()
    return "", 204


@app.route('/data_backend/search_list_result', methods=['POST'])
def get_search_list_result_endpoint():
    # turn params into string to make it cachable (aka hashable):
    params_str = json.dumps(request.json, indent=2)
    # ignore_cache = request.args.get('ignore_cache') == "true"
    # print(params_str)
    try:
        result = get_search_results(params_str, purpose='list')
    except ValueError as e:
        print(e)
        import traceback
        traceback.print_exc()
        return str(e.args), 400  # TODO: there could be other reasons, e.g. dataset not found

    response = app.response_class(
        response=json.dumps(result, cls=CustomJSONEncoder),  # type: ignore
        mimetype='application/json'
    )
    return response


@app.route('/data_backend/question_context', methods=['POST'])
def get_question_context():
    # turn params into string to make it cachable (aka hashable):
    data: dict | None = request.json
    if not data:
        return "no data", 400
    data["search_settings"]["result_list_items_per_page"] = 4
    data["search_settings"]["search_algorithm"] = "vector"
    params_str = json.dumps({'search': data["search_settings"]}, indent=2)
    # ignore_cache = request.args.get('ignore_cache') == "true"
    # print(params_str)
    try:
        result = get_search_results(params_str, purpose='list')
    except ValueError as e:
        print(e)
        import traceback
        traceback.print_exc()
        return str(e.args), 400  # TODO: there could be other reasons, e.g. dataset not found

    sorted_ids = result["sorted_ids"]
    items_by_dataset = result['items_by_dataset']

    context = ""
    for ds_id, item_id in sorted_ids:
        item = items_by_dataset[ds_id][item_id]
        context += f"Item: [{ds_id}, {item_id}]\n"
        for field in item:
            if field.startswith("_"):
                continue
            context += f"  {field}: {item[field]}\n"
        chunk_fields_with_relevant_parts = [part.get('field') for part in item.get("_relevant_parts", []) if part.get("index") is not None]
        if chunk_fields_with_relevant_parts:
            item_with_chunk_fields = get_document_details_by_id(ds_id, item_id, tuple(chunk_fields_with_relevant_parts), None)
            assert item_with_chunk_fields is not None
            for part in item["_relevant_parts"]:
                if part.get("index") is None:
                    # TODO: add relevant parts from keyword search, too (change to hybrid above and increase highlights length in OpenSearch)
                    continue
                chunk_before = item_with_chunk_fields.get(part.get("field"), [])[part.get("index") - 1].get('text', '') if part.get("index") > 0 else ""
                this_chunk = item_with_chunk_fields.get(part.get("field"), [])[part.get("index")].get('text', '')
                chunk_after = item_with_chunk_fields.get(part.get("field"), [])[part.get("index") + 1].get('text', '') if part.get("index") < part.get('array_size', 0) else ""
                text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
                context += f"  Potentially Relevant Snippet from {part.get('field')}:\n"
                context += f"    {text}\n"
        context += "\n"

    response = app.response_class(
        response=json.dumps({'context': context}, cls=CustomJSONEncoder),  # type: ignore
        mimetype='application/json'
    )
    return response


@app.route('/data_backend/delete_dataset_content', methods=['POST'])
def delete_dataset_content_endpoint():
    # FIXME: check permissions
    try:
        dataset_id: int = request.json["dataset_id"]  # type: ignore
    except KeyError:
        return "dataset_id missing", 400
    try:
        delete_dataset_content(dataset_id)
    except Exception as e:
        raise e
        return str(e), 500
    return "", 204


@app.route('/data_backend/upload_files', methods=['POST'])
def upload_files_endpoint():
    # TODO: check auth
    try:
        dataset_id: int = int(request.form["dataset_id"])
        import_converter_id: int = int(request.form["import_converter_id"])
    except KeyError as e:
        return f"parameter missing: {e}", 400
    inserted_ids, failed_files = upload_files(dataset_id, import_converter_id, request.files.getlist("files[]"))
    return jsonify({"inserted_ids": inserted_ids, "failed_files": failed_files}), 200


# --- Old Routes: ---


@app.route('/data_backend/map', methods=['POST'])
def get_or_create_map_endpoint():
    params = DotDict(request.json or {})
    ignore_cache = request.args.get('ignore_cache') == "true"

    map_id = get_or_create_map(params, ignore_cache)

    return jsonify({"map_id": map_id})


@app.route('/data_backend/map/result', methods=['POST'])
def retrive_map_results():
    params = request.json or {}
    map_id = params.get("map_id")
    exclude_fields = params.get("exclude_fields", [])
    result = get_map_results(map_id)
    if result is None:
        return "map_id not found", 404
    result = deepcopy(result)

    for field in list(result['results']['per_point_data'].keys()):
        if field in exclude_fields:
            del result['results']['per_point_data'][field]

    if 'search_result_score_info' in exclude_fields and 'search_result_score_info' in result['results']:
        del result['results']['search_result_score_info']
    if 'clusters' in exclude_fields and 'clusters' in result['results']:
        del result['results']['clusters']
    if 'parameters' in exclude_fields and 'parameters' in result:
        del result['parameters']
    if 'slimmed_items_per_dataset' in exclude_fields and 'slimmed_items_per_dataset' in result['results']:
        del result['results']['slimmed_items_per_dataset']
    if 'last_parameters' in exclude_fields and 'last_parameters' in result:
        del result['last_parameters']
    if 'thumbnail_atlas_filename' in exclude_fields and 'thumbnail_atlas_filename' in result['results']:
        del result['results']['thumbnail_atlas_filename']
    if 'full_items_per_dataset' in result['results']:
        # always exclude full items
        del result['results']['full_items_per_dataset']

    if params.get("last_position_update_received") and 'last_position_update' in result['results']:
        if result['results']['last_position_update'] <= params["last_position_update_received"]:
            # most up-to-date data already received
            if 'positions_x' in result['results']['per_point_data']:
                del result['results']['per_point_data']['positions_x']
            if 'positions_y' in result['results']['per_point_data']:
                del result['results']['per_point_data']['positions_y']

    use_cbor = request.headers.get('Accept') == "application/cbor"
    if use_cbor:
        resp = app.make_response(cbor2.dumps(result))
        resp.mimetype = "application/cbor"
        return resp
    return result


@app.route('/data_backend/stored_map/parameters_and_search_results', methods=['POST'])
def retrive_parameters_and_search_results_for_stored_map():
    # FIXME: this doesn't support paging in the future
    params = request.json or {}
    map_id = params.get("map_id")
    map_data = get_map_results(map_id)
    if map_data is None:
        return "map_id not found", 404

    result = get_search_results_for_stored_map(map_data)
    result['parameters'] = deepcopy(map_data['parameters'])
    return result


@app.route('/data_backend/map/thumbnail_atlas/<filename>', methods=['GET'])
def retrieve_thumbnail_atlas(filename):
    full_path = os.path.join(THUMBNAIL_ATLAS_DIR, filename)
    if filename is None or not os.path.exists(full_path):
        return "texture atlas not found", 404

    return send_from_directory(THUMBNAIL_ATLAS_DIR, filename)


@app.route('/data_backend/local_image/<path:image_path>', methods=['GET'])
def retrieve_local_image(image_path):
    # FIXME: this is just a hacky way to make Kaggle Fashion images stored in /data work
    image_path = "/" + image_path
    if image_path is None or not os.path.exists(image_path):
        return "image not found", 404

    return send_from_directory('/data/', image_path.replace("/data/", ""))


@app.route('/data_backend/download_file/<path:file_path>', methods=['GET'])
def download_file(file_path):
    path = f'{UPLOADED_FILES_FOLDER}/{file_path}'
    if not os.path.exists(path):
        return "file not found", 404

    return send_from_directory(UPLOADED_FILES_FOLDER, file_path)


@app.route('/data_backend/document/details_by_id', methods=['POST'])
def retrieve_document_details_by_id():
    params = request.json or {}
    dataset_id = params.get("dataset_id")
    item_id = params.get("item_id")
    fields: list[str] = params.get("fields") # type: ignore
    relevant_parts = params.get("relevant_parts")
    if not all([dataset_id is not None, item_id is not None, fields is not None]):
        return "a parameter is missing", 400

    if relevant_parts:
        # need to convert to json string to make it hashable for caching
        relevant_parts = json.dumps(relevant_parts)
    result = get_document_details_by_id(dataset_id, item_id, tuple(fields), relevant_parts)

    if result is None:
        return "document not found", 404

    return result


@app.route('/data_backend/map/store', methods=['POST'])
def store_map():
    params = request.json or {}
    user_id = params.get("user_id")
    organization_id = params.get("organization_id")
    name = params.get("name")
    display_name = params.get("display_name")
    map_id = params.get("map_id")

    if not all([user_id is not None, organization_id is not None, name, display_name, map_id is not None]):
        return "a parameter is missing", 400

    map_data = get_map_results(map_id)
    if map_data is None:
        return "map not found", 404

    result = add_stored_map(map_id, user_id, organization_id, name, display_name, map_data)

    return result


# -------------------- DataCollections --------------------

@app.route('/data_backend/classifier/retraining_status', methods=['POST'])
def get_retraining_status_route():
    params = request.json or {}
    params = DotDict(params)
    status = get_retraining_status(params.collection_id, params.class_name, params.embedding_space_id)
    return jsonify(status)


@app.route('/data_backend/classifier/retrain', methods=['POST'])
def start_retrain_route():
    params = request.json or {}
    params = DotDict(params)
    start_retrain(params.collection_id, params.class_name, params.embedding_space_id, params.deep_train)
    return "", 204


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=55123, debug=True)
