from collections import defaultdict
import os
import json
import logging
import re
from typing import Generator, Iterable, Optional

from opensearchpy import OpenSearch
import opensearchpy.helpers

from database_client.remote_instance_client import use_remote_db

from utils.dotdict import DotDict
from utils.field_types import FieldType
from utils.custom_json_encoder import CustomJSONEncoder
from utils.helpers import run_in_batches_without_result
from utils.source_plugin_types import SourcePlugin


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
            timeout = 90,  # seconds, especially on AWS EBS volumes, requests can take very long
        )


    @staticmethod
    def get_instance() -> "TextSearchEngineClient":
        if TextSearchEngineClient._instance is None:
            TextSearchEngineClient._instance = TextSearchEngineClient()
        return TextSearchEngineClient._instance


    def ensure_dataset_exists(self, dataset: dict):
        # create dataset
        # create indexes
        # check if dataset is still valid, update if necessary
        dataset = DotDict(dataset)
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            # for remote instances, we assume the database already exists
            return

        index_name = dataset.actual_database_name
        index_body = {}
        try:
            response = self.client.indices.create(index_name, body=index_body)
        except Exception as e:
            logging.error(f"Error during creating index: type {type(e)}, error: {e}")
            # opensearchpy.exceptions.RequestError: RequestError(400, 'resource_already_exists_exception', 'index [dataset_4/1kYO7nOKQm2LMbosdiPeXw] already exists')
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
            FieldType.CHUNK: "flat_object",
        })

        # almost all field types can be arrays in OpenSearch, except for a few which need a different type (e.g. rank_features)
        array_field_type_to_open_search_type = field_type_to_open_search_type.copy()
        array_field_type_to_open_search_type.update({
            FieldType.CLASS_PROBABILITY: "rank_features",  # NOTE: "s" for multiple class probabilities (without creating new fields for each)
        })

        for field in dataset.object_fields.values():
            if field.identifier == "_id":
                continue
            if field.field_type == FieldType.VECTOR:
                continue
            open_search_type = array_field_type_to_open_search_type[field.field_type] if field.is_array else field_type_to_open_search_type[field.field_type]
            properties[field.identifier] = {"type": open_search_type}
            # all field types except for object and flat_object support the "index" parameter
            if open_search_type not in ("object", "flat_object"):
                indexed = (field.is_available_for_search or field.is_available_for_filtering) and field.field_type != FieldType.VECTOR
                properties[field.identifier]["index"] = indexed
            if field.field_type == FieldType.TEXT and field.language_analysis:
                properties[field.identifier]["analyzer"] = field.language_analysis

        mappings = {
            'properties': properties,
        }
        try:
            response = self.client.indices.put_mapping(index=index_name, body=mappings)
        except Exception as e:
            logging.error(f"Error during updating text search engine mapping: type {type(e)}, error: {e}")
            raise e
        else:
            logging.info(f"Successfully changed text search engine mapping: {response}")


    def remove_dataset(self, dataset: DotDict):
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return
        index_name = dataset.actual_database_name
        self.client.indices.delete(index=index_name, ignore_unavailable=True)  # type: ignore


    def get_item_count(self, dataset: DotDict) -> int:
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="get_item_count",
                arguments={}
            )
        index_name = dataset.actual_database_name
        response = self.client.count(index=index_name, ignore_unavailable=True)  # type: ignore
        return response["count"]


    def get_random_items(self, index_name: str, count: int, required_fields: Optional[list[str]] = None):
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
            index = index_name
        )
        return response.get("hits", {}).get("hits", [])


    def upsert_items(self, index_name: str, ids: Iterable[str], payloads: Iterable[dict]):

        def upsert_batch(ids_and_payloads):
            bulk_operations = ""
            for _id, item in ids_and_payloads:
                op = { "update" : { "_index" : index_name, "_id" : _id } }
                item = item.copy()
                item.pop("_id")
                bulk_operations += json.dumps(op) + "\n" + json.dumps({'doc': item, 'doc_as_upsert': True}, cls=CustomJSONEncoder) + "\n"

            response = self.client.bulk(body=bulk_operations)
            if response.get("errors"):
                error_items = []
                if response.get("items"):
                    for item in response["items"]:
                        if item.get("update"):
                            if item["update"].get("error"):
                                error_items.append(item)
                if error_items:
                    logging.error(repr(error_items))
                    raise ValueError(error_items)
                else:
                    logging.error(f"Error during upserting items: {response}")
                    raise ValueError(response)

        run_in_batches_without_result(list(zip(ids, payloads)), 512, upsert_batch)


    def remove_items(self, dataset_id: str, primary_key_field: str, item_pks: list[str]):
        pass


    def get_items_by_ids(self, dataset: DotDict, ids: Iterable[str], fields: Iterable[str]) -> list:
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="get_items_by_ids",
                arguments={"ids": ids, "fields": fields}
            )
        body = {
            "ids": ids,
        }
        index_name = dataset.actual_database_name
        response = self.client.mget(body=body, index=index_name, params={"_source_includes": ",".join(fields)})
        items = []
        for doc in response['docs']:
            item = doc["_source"]
            item["_id"] = doc["_id"]
            items.append(item)
        return items


    def get_all_items_with_missing_field_count(self, index_name: str, missing_field: str) -> int:
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
        response = self.client.count(index=index_name, body=query, ignore_unavailable=True)  # type: ignore
        return response["count"]


    def get_all_items_with_missing_field(self, index_name: str, missing_field: str, required_fields: list[str], internal_batch_size: int = 1000) -> Generator:
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


    def delete_field(self, index_name: str, field):
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


    def get_search_results(self, dataset: DotDict, search_fields, filters: list[dict],
                           query_positive, query_negative, page, limit, return_fields,
                           highlights=False, use_bolding_in_highlights:bool=True):
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="get_search_results",
                arguments={"search_fields": search_fields, "filters": filters, "query_positive": query_positive,
                            "query_negative": query_negative, "page": page, "limit": limit, "return_fields": return_fields,
                            "highlights": highlights, "use_bolding_in_highlights": use_bolding_in_highlights}
            )
        if filters:
            query = {
                'size': limit,
                'query': {
                    'bool': {
                        'filter': self._convert_to_opensearch_filters(filters),
                    }
                },
                '_source': return_fields,
            }
            if query_positive:
                query['query']['bool']['must'] = {
                    'simple_query_string': {
                        'query': self._convert_to_simple_query_language(query_positive),
                        'fields': search_fields,
                        'default_operator': 'and',
                    }
                }
        else:
            query = {
                'size': limit,
                'query': {
                    'simple_query_string': {
                        'query': self._convert_to_simple_query_language(query_positive),
                        'fields': search_fields,
                        'default_operator': 'and',
                    }
                },
                '_source': return_fields,
            }
        if highlights:
            query['highlight'] = {
                "fields": {field: {} for field in search_fields},
                "number_of_fragments": 2,
                "order": "score",
                "pre_tags": ["<b>"] if use_bolding_in_highlights else [""],
                "post_tags": ["</b>"] if use_bolding_in_highlights else [""],
                "fragment_size": 400,
            }

        response = self.client.search(
            body = query,
            index = dataset.actual_database_name,
        )
        total_matches = response.get("hits", {}).get("total", {}).get("value", 0)
        return response.get("hits", {}).get("hits", []), total_matches


    def _convert_to_opensearch_filters(self, filters: list[dict]):
        query_filter = {
            'bool': {
                'must': [],
                'must_not': [],
            },
        }
        for filter_ in filters:
            filter_ = DotDict(filter_)
            if filter_.operator == "contains":
                if isinstance(filter_.field, list):
                    f = {
                        "bool": {
                            "should": []
                        }
                    }
                    for field in filter_.field:
                        f["bool"]["should"].append({
                            "match_phrase": {
                                field: filter_.value
                            }
                        })
                    query_filter['bool']['must'].append(f)
                else:
                    query_filter['bool']['must'].append({
                        "match_phrase": {
                            filter_.field: filter_.value
                        }
                    })
            elif filter_.operator == "does_not_contain":
                query_filter['bool']['must_not'].append({
                    "match_phrase": {
                        filter_.field: filter_.value
                    }
                })
            elif filter_.operator in ("is", "is_not"):
                # Note: also works to check if an element is in an array
                query_filter['bool']['must' if filter_.operator == "is" else 'must_not'].append({
                    "term": {
                        filter_.field: {
                            "value": filter_.value,
                            "case_insensitive": True
                        }
                    }
                })
            elif filter_.operator == "is_empty":
                query_filter["bool"]["must"].append(
                    {
                        "bool": {
                            "should": [
                                {
                                    "bool": {
                                        "must_not": [
                                            {"exists": {"field": filter_.field}}
                                        ]
                                    }
                                },
                                {"term": {filter_.field: ""}},
                            ]
                        }
                    }
                )
            elif filter_.operator == "is_not_empty":
                query_filter["bool"]["must"].append({"exists": {"field": filter_.field}})
                query_filter["bool"]["must"].append({"bool": {"must_not": [{"term": {filter_.field: ""}}]}})
            elif filter_.operator in ("lt", "lte", "gt", "gte"):
                query_filter['bool']['must'].append({
                    "range": {
                        filter_.field: {
                            filter_.operator: filter_.value
                        }
                    }
                })
        return query_filter


    def _convert_to_simple_query_language(self, query: str):
        conversion = {"AND": "+", "OR": "|", r"NOT\s+": "-"}
        for old, new in conversion.items():
            query = re.sub(old, new, query)
        return query
