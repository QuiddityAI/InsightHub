import json
import os

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug import serving

from utils.custom_json_encoder import CustomJSONEncoder
from utils.dotdict import DotDict

from logic.mapping_task import get_or_create_map, get_map_results
from logic.insert_logic import insert_many, update_database_layout
from logic.search import get_search_results, get_document_details_by_id

from database_client.django_client import add_stored_map


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

# How to make it customizable and still offer default search and map for schemas?
# -> as currently, offer all settings in UI and select basic defaults based on schema
# How to apply search and map settings to different schemas (with different field names etc.)?
# Schema could have default set of vector and text search / map fields, but
# what if there should be two search / map settings for the same schema?
# E.g. for products, search in title only or in reviews, map based on image or on reviews
# Should search and map settings be separated? Would map always use same search settings as list?
# map might be enriched much more, clustering might be done on different aspect (only image, not title)
# given 100 products all called "white t-shirt", search by title but map by image

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
def get_search_list_result_endpoint():
    # turn params into string to make it cachable (aka hashable):
    params_str = json.dumps(request.json, indent=2)
    # print(params_str)
    try:
        result = get_search_results(params_str, purpose='list')
    except ValueError as e:
        print(e)
        import traceback
        traceback.print_exc()
        return str(e.args), 400  # TODO: there could be other reasons, e.g. schema not found

    response = app.response_class(
        response=json.dumps(result, cls=CustomJSONEncoder),
        mimetype='application/json'
    )
    return response


# --- Old Routes: ---


@app.route('/data_backend/map', methods=['POST'])
def get_or_create_map_endpoint():
    params = DotDict(request.json or {})

    map_id = get_or_create_map(params)

    return jsonify({"map_id": map_id})


@app.route('/data_backend/map/result', methods=['POST'])
def retrive_map_results():
    params = request.json or {}
    map_id = params.get("map_id")
    result = get_map_results(map_id)

    if result is None:
        return "map_id not found", 404

    return result


@app.route('/data_backend/map/texture_atlas/<subfolder>/<image_path>', methods=['GET'])
def retrieve_texture_atlas(subfolder, image_path):
    full_path = os.path.join(subfolder, image_path)
    if image_path is None or not os.path.exists(full_path):
        return "texture atlas not found", 404

    return send_from_directory('.', full_path)


@app.route('/data_backend/document/details_by_id', methods=['POST'])
def retrieve_document_details_by_id():
    params = request.json or {}
    schema_id = params.get("schema_id")
    item_id = params.get("item_id")
    fields: list[str] = params.get("fields") # type: ignore
    if not all([schema_id is not None, item_id is not None, fields is not None]):
        return "a parameter is missing", 400

    result = get_document_details_by_id(schema_id, item_id, tuple(fields))

    if result is None:
        return "document not found", 404

    return result


@app.route('/data_backend/map/store', methods=['POST'])
def store_map():
    params = request.json or {}
    user_id = params.get("user_id")
    schema_id = params.get("schema_id")
    name = params.get("name")
    map_id = params.get("map_id")

    if not all([user_id is not None, schema_id is not None, name, map_id is not None]):
        return "a parameter is missing", 400

    map_data = get_map_results(map_id)
    if map_data is None:
        return "map not found", 404

    result = add_stored_map(map_id, user_id, schema_id, name, map_data)

    return result


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=55123, debug=True)
