from collections import defaultdict
from hashlib import md5
import json

# global temp storage:
local_maps = {}

vectorize_stage_hash_to_map_id = defaultdict(list)

projection_stage_hash_to_map_id = defaultdict(list)


def clear_local_map_cache():
    global local_maps
    global vectorize_stage_hash_to_map_id
    global projection_stage_hash_to_map_id
    local_maps = {}
    vectorize_stage_hash_to_map_id = defaultdict(list)
    projection_stage_hash_to_map_id = defaultdict(list)


def get_map_parameters_hash(parameters: dict) -> str:
    parameters_hash = md5(json.dumps(parameters).encode()).hexdigest()
    return parameters_hash


def get_search_stage_hash(parameters: dict) -> str:
    relevant_parameters = {
        "search": parameters.get('search', {}),
    }
    hash = md5(json.dumps(relevant_parameters).encode()).hexdigest()
    return hash


def get_vectorize_stage_hash(parameters: dict) -> str:
    vectorize_stage_parameters = {
        "search": parameters.get('search', {}),
        "vectorize": parameters.get('vectorize', {}),
    }
    vectorize_stage_hash = md5(json.dumps(vectorize_stage_parameters).encode()).hexdigest()
    return vectorize_stage_hash


def get_projection_stage_hash(parameters: dict) -> str:
    projection_stage_parameters = {
        "search": parameters.get('search', {}),
        "vectorize": parameters.get('vectorize', {}),
        "projection": parameters.get('projection', {}),
    }
    projection_stage_hash = md5(json.dumps(projection_stage_parameters).encode()).hexdigest()
    return projection_stage_hash
