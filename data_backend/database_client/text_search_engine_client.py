from collections import defaultdict
import os
import json
import logging
from typing import Generator, Iterable, Optional

from opensearchpy import OpenSearch
import opensearchpy.helpers

from utils.dotdict import DotDict
from utils.field_types import FieldType
from utils.custom_json_encoder import CustomJSONEncoder
from utils.helpers import run_in_batches_without_result


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
            http_compress = False, # gzip compression for request bodies
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
            logging.error(f"Error during creating index: type {type(e)}, error: {e}")
            # opensearchpy.exceptions.RequestError: RequestError(400, 'resource_already_exists_exception', 'index [schema_4/1kYO7nOKQm2LMbosdiPeXw] already exists')
        else:
            logging.info(response)

        properties = {}

        field_type_to_open_search_type = defaultdict(lambda: "text")
        field_type_to_open_search_type.update({
            FieldType.TEXT: "text",
            FieldType.TAG: "keyword",
            FieldType.INTEGER: "integer",
            FieldType.FLOAT: "float",
            FieldType.CLASS_PROBABILITY: "rank_feature",  # NOTE: no "s" at the end, singular class probability
            FieldType.BOOL: "boolean",
            FieldType.DATE: "date",
            FieldType.DATETIME: "date",
            FieldType.IDENTIFIER: "text",
            FieldType.URL: "text",
            FieldType.VECTOR: "knn_vector",  # in ElasticSearch, its called "dense_vector"
            FieldType.ATTRIBUTES: "object",
            FieldType.ARBITRARY_OBJECT: "flat_object",
        })

        # almost all field types can be arrays in OpenSearch, except for a few which need a different type (e.g. rank_features)
        array_field_type_to_open_search_type = field_type_to_open_search_type.copy()
        array_field_type_to_open_search_type.update({
            FieldType.CLASS_PROBABILITY: "rank_features",  # NOTE: "s" for multiple class probabilities (without creating new fields for each)
        })

        for field in schema.object_fields.values():
            if field.identifier == "_id":
                continue
            if field.field_type == FieldType.VECTOR:
                continue
            open_search_type = array_field_type_to_open_search_type[field.field_type] if field.is_array else field_type_to_open_search_type[field.field_type]
            properties[field.identifier] = {"type": open_search_type}
            # all field types except for object and flat_object support the "index" parameter
            if field.field_type not in (FieldType.ATTRIBUTES, FieldType.ARBITRARY_OBJECT):
                indexed = (field.is_available_for_search or field.is_available_for_filtering) and field.field_type != FieldType.VECTOR
                properties[field.identifier]["index"] = indexed
            if field.field_type == FieldType.TEXT and field.language_analysis:
                properties[field.identifier]["analyzer"] = field.language_analysis

        mappings = {
            'properties': properties,
        }
        try:
            response = self.client.indices.put_mapping(index=self._get_index_name(schema.id), body=mappings)
        except Exception as e:
            logging.error(f"Error during updating text search engine mapping: type {type(e)}, error: {e}")
            raise e
        else:
            logging.info(f"Successfully changed text search engine mapping: {response}")


    def remove_schema(self, schema_id: str):
        pass


    def get_item_count(self, schema_id: int):
        index_name = self._get_index_name(schema_id)
        response = self.client.count(index=index_name)
        return response["count"]


    def get_random_items(self, schema_id: int, count: int, required_fields: Optional[list[str]] = None):
        query = {
            "size": count,
            "query": {
                "function_score": {
                    "functions": [{
                        "random_score": {}
                    }]
                }
            }
        }
        if required_fields is not None:
            query["_source"] = required_fields
        response = self.client.search(
            body = query,
            index = self._get_index_name(schema_id)
        )
        return response.get("hits", {}).get("hits", [])


    def upsert_items(self, schema_id: int, ids: list[str], payloads: list[dict]):
        index_name = self._get_index_name(schema_id)

        def upsert_batch(ids_and_payloads):
            bulk_operations = ""
            for _id, item in ids_and_payloads:
                op = { "update" : { "_index" : index_name, "_id" : _id } }
                item = item.copy()
                item.pop("_id")
                bulk_operations += json.dumps(op) + "\n" + json.dumps({'doc': item, 'doc_as_upsert': True}, cls=CustomJSONEncoder) + "\n"

            response = self.client.bulk(body=bulk_operations)
            if response.get("errors"):
                logging.error(repr(response))
                raise ValueError(response)

        run_in_batches_without_result(list(zip(ids, payloads)), 512, upsert_batch)


    def remove_items(self, schema_id: str, primary_key_field: str, item_pks: list[str]):
        pass


    def get_items_by_ids(self, schema_id: int, ids: Iterable[str], fields: Iterable[str]) -> list:
        index_name = self._get_index_name(schema_id)
        body = {
            "ids": ids,
        }
        response = self.client.mget(body=body, index=index_name, params={"_source_includes": ",".join(fields)})
        items = []
        for doc in response['docs']:
            item = doc["_source"]
            item["_id"] = doc["_id"]
            items.append(item)
        return items


    def get_all_items_with_missing_field_count(self, schema_id: int, missing_field: str) -> int:
        index_name = self._get_index_name(schema_id)
        query = {
            "query": {
                "bool": {
                    "must_not": {
                        "exists": {
                            "field": missing_field
                        }
                    }
                }
            }
        }
        response = self.client.count(index=index_name, body=query)
        return response["count"]


    def get_all_items_with_missing_field(self, schema_id: int, missing_field: str, required_fields: list[str], internal_batch_size: int = 1000) -> Generator:
        index_name = self._get_index_name(schema_id)
        query = {
            '_source': required_fields,
            "query": {
                "bool": {
                    "must_not": {
                        "exists": {
                            "field": missing_field
                        }
                    }
                }
            }
        }
        generator = opensearchpy.helpers.scan(
            self.client,
            index=index_name,
            query=query,
            size=internal_batch_size,
            scroll="10m",  # time to keep the search context alive to get the next batch of results
        )
        for doc in generator:
            item = doc["_source"]
            item["_id"] = doc["_id"]
            yield item


    def delete_field(self, schema_id, field):
        index_name = self._get_index_name(schema_id)

        body = {
            "query": {
                "match_all": {},
            },
            "script" : {
                "source": f"ctx._source.remove('{field}')",
            }
        }

        response = self.client.update_by_query(index=index_name, body=body)
        logging.warning(f"Deleted field {field} from text search engine: {response}")


    def get_search_results(self, schema_id, search_fields, filter_criteria, query_positive, query_negative, page, limit, return_fields, highlights=False):
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
        if highlights:
            query['highlight'] = {
                "fields": {field: {} for field in search_fields}
            }

        response = self.client.search(
            body = query,
            index = self._get_index_name(schema_id)
        )
        return response.get("hits", {}).get("hits", [])
