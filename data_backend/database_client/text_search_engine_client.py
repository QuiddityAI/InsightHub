import os
import json
import logging
from uuid import UUID

from opensearchpy import OpenSearch

from utils.dotdict import DotDict
from utils.field_types import FieldType
from utils.custom_json_encoder import CustomJSONEncoder


with open("../credentials.json", "rb") as f:
    credentials = json.load(f)

open_search_host = os.getenv("search_engine_host", 'localhost')
open_search_port = 9200
open_search_auth = (credentials["open_search_user"], credentials["open_search_password"])


class TextSearchEngineClient(object):

    # using a singleton here to have only one DB connection, but lazy-load it only when used to speed up startup time
    _instance: "TextSearchEngineClient" = None # type: ignore


    def __init__(self):
        self.client = OpenSearch(
            hosts = [{'host': open_search_host, 'port': open_search_port}],
            http_compress = True, # enables gzip compression for request bodies
            http_auth = open_search_auth,
            use_ssl = True,
            verify_certs = False,
            ssl_assert_hostname = False,
            ssl_show_warn = False,
        )


    @staticmethod
    def get_instance() -> "TextSearchEngineClient":
        if TextSearchEngineClient._instance is None:
            TextSearchEngineClient._instance = TextSearchEngineClient()
        return TextSearchEngineClient._instance


    def _get_index_name(self, schema_id: int):
        return f'schema_{schema_id}'


    def ensure_schema_exists(self, schema: dict):
        # create schema
        # create indexes
        # check if schema is still valid, update if necessary
        schema = DotDict(schema)

        index_name = self._get_index_name(schema.id)
        index_body = {}
        try:
            response = self.client.indices.create(index_name, body=index_body)
        except Exception as e:
            print(type(e), e)
            # opensearchpy.exceptions.RequestError: RequestError(400, 'resource_already_exists_exception', 'index [schema_4/1kYO7nOKQm2LMbosdiPeXw] already exists')
        else:
            print(response)

        properties = {}

        field_type_to_open_search_type = {
            FieldType.TEXT: "text",
            FieldType.TAG: "keyword",
            FieldType.INTEGER: "integer",
            FieldType.FLOAT: "float",
            FieldType.CLASS_PROBABILITY: "rank_feature",
            FieldType.BOOL: "boolean",
        }

        for field in schema.object_fields.values():
            if field.is_available_for_search and field.field_type == FieldType.TEXT:
                properties[field.identifier] = {"type": "text"}
            elif field.is_available_for_filtering:
                if field.field_type not in field_type_to_open_search_type:
                    logging.error(f"Field type not yet supported for filtering: {field.identifier}, {field.field_type}")
                    continue
                properties[field.identifier] = {"type": field_type_to_open_search_type[field.field_type]}

        mappings = {
            'properties': properties,
        }
        try:
            response = self.client.indices.put_mapping(index=self._get_index_name(schema.id), body=mappings)
        except Exception as e:
            print(type(e), e)
            raise e
        else:
            print(response)


    def remove_schema(self, schema_id: str):
        pass


    def upsert_items(self, schema_id: int, ids: list[UUID], payloads: list[dict]):
        index_name = self._get_index_name(schema_id)

        bulk_operations = ""
        for _id, item in zip(ids, payloads):
            op = { "index" : { "_index" : index_name, "_id" : str(_id) } }
            bulk_operations += json.dumps(op) + "\n" + json.dumps(item, cls=CustomJSONEncoder) + "\n"

        response = self.client.bulk(body=bulk_operations)
        # print(response)


    def remove_items(self, schema_id: str, primary_key_field: str, item_pks: list[str]):
        pass


    def get_items_by_primary_keys(self, schema_id: str, primary_key_field: str,
                                  item_pks: list[str], fields: list[str]) -> list[dict]:
        # mongo.get(schema=schema_id, where primary_key_field in primary_key)
        return []


    def get_all_items_with_missing_field_count(self, schema_id, missing_field) -> int:
        return 0


    def get_all_items_with_missing_field(self, schema_id, missing_field, per_page, offset) -> list[dict]:
        return []


    def clear_field(self, schema_id, field):
        return


    def get_search_results(self, schema_id, search_fields, filter_criteria, query_positive, query_negative, page, limit, return_fields):
        query = {
            'size': limit,
            'query': {
                'multi_match': {
                    'query': query_positive,
                    'fields': search_fields,
                }
            },
            '_source': return_fields,
        }

        response = self.client.search(
            body = query,
            index = self._get_index_name(schema_id)
        )
        logging.warning(response)
        return response.get("hits", {}).get("hits", [])
