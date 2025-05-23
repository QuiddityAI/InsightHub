import json
import logging
import os
import re
from collections import defaultdict
from typing import Generator, Iterable, Optional

import opensearchpy.helpers
from opensearchpy import OpenSearch, RequestError

from data_map_backend.models import Dataset
from data_map_backend.utils import DotDict
from legacy_backend.database_client.remote_instance_client import use_remote_db
from legacy_backend.utils.custom_json_encoder import CustomJSONEncoder
from legacy_backend.utils.field_types import FieldType
from legacy_backend.utils.helpers import run_in_batches_without_result
from legacy_backend.utils.source_plugin_types import SourcePlugin

open_search_host = os.getenv("search_engine_host", "localhost")
open_search_port = 9200
open_search_auth = (os.getenv("OPENSEARCH_USERNAME"), os.getenv("OPENSEARCH_PASSWORD"))


class TextSearchEngineClient(object):
    # using a singleton here to have only one DB connection, but lazy-load it only when used to speed up startup time
    _instance: "TextSearchEngineClient" = None  # type: ignore

    def __init__(self):
        self.client = OpenSearch(
            hosts=[{"host": open_search_host, "port": open_search_port}],
            http_compress=False,  # gzip compression for request bodies
            http_auth=open_search_auth,
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=90,  # seconds, especially on AWS EBS volumes, requests can take very long
            pool_maxsize=25,  # default is 10, but we have a lot of parallel requests (to get rid of "Connection pool is full" errors)
        )

    @staticmethod
    def get_instance() -> "TextSearchEngineClient":
        if TextSearchEngineClient._instance is None:
            TextSearchEngineClient._instance = TextSearchEngineClient()
        return TextSearchEngineClient._instance

    def check_status(self) -> bool:
        status = self.client.cluster.health()
        return status["status"] in ("green", "yellow")

    def ensure_dataset_exists(self, dataset: dict):
        # create dataset
        # create indexes
        # check if dataset is still valid, update if necessary
        dataset = DotDict(dataset)
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            # for remote instances, we assume the database already exists
            return

        index_name = dataset.actual_database_name
        index_body = {
            "settings": {
                "analysis": {
                    "filter": {
                        "german_synonym": {"type": "synonym", "synonyms_path": "german_synonym.txt"},
                        "german_decompounder": {
                            "type": "hyphenation_decompounder",
                            "word_list_path": "german_decompound.txt",
                            "hyphenation_patterns_path": "hyphenation_patterns_de_DR.xml",
                            "only_longest_match": True,  # see https://discuss.elastic.co/t/compound-word-token-filter-only-longest-match-doesnt-work-as-expected-in-some-scenarios/195470
                            "min_subword_size": 3,
                        },
                        "german_stemmer": {"type": "stemmer", "language": "light_german"},
                        "german_stop": {"type": "stop", "stopwords": "_german_", "remove_trailing": False},
                    },
                    "analyzer": {
                        "german_no_decompound": {
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "german_stop",
                                "german_normalization",  # replaces umlauts with their base characters
                                "german_stemmer",
                            ],
                        },
                        "german_decompound": {
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "german_stop",
                                "german_normalization",  # replaces umlauts with their base characters
                                "german_decompounder",
                                "german_stemmer",
                            ],
                        },
                        "german_decompound_synonyms": {
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "german_normalization",
                                "german_decompounder",
                                "german_synonym",  # must be before german_stop, as otherwise parsing the synonyms doesn't work because stopwords are removed
                                "german_stop",
                                "german_stemmer",
                            ],
                        },
                    },
                }
            }
        }
        try:
            response = self.client.indices.create(index_name, body=index_body)
        except RequestError as e:
            if e.error == "resource_already_exists_exception":
                logging.warning(f"Index {index_name} already exists, continuing.")
            else:
                logging.error(
                    f"Error during creating index: type {type(e)}, error: {e}, info: {e.info}, status_code: {e.status_code}"
                )
                raise e
        except Exception as e:
            logging.warning(f"Error during creating index: type {type(e)}, error: {e}")
            raise e
        else:
            logging.info(response)

        properties = {}

        field_type_to_open_search_type = defaultdict(lambda: "text")
        field_type_to_open_search_type.update(
            {
                FieldType.TEXT: "text",
                FieldType.STRING: "text",
                FieldType.TAG: "keyword",
                FieldType.INTEGER: "integer",
                FieldType.FLOAT: "float",
                FieldType.CLASS_PROBABILITY: "rank_feature",  # NOTE: no "s" at the end, singular class probability
                FieldType.BOOL: "boolean",
                FieldType.DATE: "date",
                FieldType.DATETIME: "date",
                FieldType.IDENTIFIER: "keyword",
                FieldType.URL: "keyword",
                FieldType.VECTOR: "knn_vector",  # in ElasticSearch, its called "dense_vector"
                FieldType.ATTRIBUTES: "object",
                FieldType.ARBITRARY_OBJECT: "flat_object",
                FieldType.CHUNK: "flat_object",
            }
        )

        # almost all field types can be arrays in OpenSearch, except for a few which need a different type (e.g. rank_features)
        array_field_type_to_open_search_type = field_type_to_open_search_type.copy()
        array_field_type_to_open_search_type.update(
            {
                FieldType.CLASS_PROBABILITY: "rank_features",  # NOTE: "s" for multiple class probabilities (without creating new fields for each)
            }
        )

        for field in dataset.schema.object_fields.values():
            if field.identifier == "_id":
                continue
            if field.field_type == FieldType.VECTOR:
                continue
            open_search_type = (
                array_field_type_to_open_search_type[field.field_type]
                if field.is_array
                else field_type_to_open_search_type[field.field_type]
            )
            properties[field.identifier] = {"type": open_search_type}
            # all field types except for object and flat_object support the "index" parameter
            if open_search_type not in ("object", "flat_object"):
                indexed = (
                    field.is_available_for_search or field.is_available_for_filtering
                ) and field.field_type != FieldType.VECTOR
                properties[field.identifier]["index"] = indexed
            if open_search_type == "text" and field.language_analysis:
                if field.language_analysis == "german":
                    properties[field.identifier]["analyzer"] = "german_decompound"
                    properties[field.identifier]["search_analyzer"] = "german_no_decompound"
                else:
                    properties[field.identifier]["analyzer"] = field.language_analysis
            if open_search_type == "text" and field.additional_language_analysis:
                for language in field.additional_language_analysis:
                    if field.language_analysis == "german":
                        properties[field.identifier]["fields"] = {
                            language: {
                                "type": "text",
                                "analyzer": "german_decompound",
                                "search_analyzer": "german_no_decompound",
                            }
                        }
                    else:
                        properties[field.identifier]["fields"] = {
                            language: {
                                "type": "text",
                                "analyzer": language,
                            }
                        }
            if field.field_type == FieldType.STRING:
                # STRING fields should be searchable by both tokenized and exact values (e.g. filenames), so we need a keyword field
                properties[field.identifier]["fields"] = {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 512,
                    }
                }

        if dataset.schema.direct_parent:
            properties["_parent"] = {"type": "keyword"}
        if dataset.schema.all_parents:
            # all_parents is a list of all parent IDs, including the direct parent
            properties["_all_parents"] = {"type": "keyword"}

        mappings = {
            "properties": properties,
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
                dataset=dataset, db_type="text_search_engine", function_name="get_item_count", arguments={}
            )
        index_name = dataset.actual_database_name
        response = self.client.count(index=index_name, ignore_unavailable=True)  # type: ignore
        return response["count"]

    def get_random_items(self, index_name: str, count: int, required_fields: Optional[list[str]] = None):
        query = {"size": count, "query": {"function_score": {"functions": [{"random_score": {}}]}}}
        if required_fields is not None:
            query["_source"] = required_fields
        response = self.client.search(body=query, index=index_name)
        return response.get("hits", {}).get("hits", [])

    def upsert_items(self, index_name: str, ids: Iterable[str], payloads: Iterable[dict]):
        def upsert_batch(ids_and_payloads):
            bulk_operations = ""
            for _id, item in ids_and_payloads:
                op = {"update": {"_index": index_name, "_id": _id}}
                item = item.copy()
                item.pop("_id")
                bulk_operations += (
                    json.dumps(op)
                    + "\n"
                    + json.dumps({"doc": item, "doc_as_upsert": True}, cls=CustomJSONEncoder)
                    + "\n"
                )

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

    def remove_items(self, dataset: DotDict | Dataset, item_ids: list[str]):
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="remove_items",
                arguments={"item_ids": item_ids},
            )
        body = {"query": {"terms": {"_id": item_ids}}}
        index_name = dataset.actual_database_name
        response = self.client.delete_by_query(index=index_name, body=body)
        logging.warning(f"Deleted items from text search engine: {response}")

    def get_items_by_ids(self, dataset: DotDict, ids: Iterable[str], fields: Iterable[str]) -> list:
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="get_items_by_ids",
                arguments={"ids": ids, "fields": fields},
            )
        body = {
            "ids": ids,
        }
        index_name = dataset.actual_database_name
        response = self.client.mget(body=body, index=index_name, params={"_source_includes": ",".join(fields)})
        items = []
        for doc in response["docs"]:
            item = doc.get(
                "_source", {}
            )  # if an item isn't found, the source is not there, return it anyway to keep order
            item["_id"] = doc["_id"]
            item["_dataset_id"] = dataset.id
            items.append(item)
        return items

    def check_item_existence(self, dataset: DotDict | Dataset, ids: Iterable[str]) -> dict:
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="check_item_existence",
                arguments={"ids": ids},
            )
        body = {
            "ids": ids,
        }
        index_name = dataset.actual_database_name
        # TODO: one source said search is better than mget, but not why (https://discuss.elastic.co/t/document-exist-check/45789/2)
        response = self.client.mget(body=body, index=index_name, params={"_source": False})
        id_exists = {}
        for doc in response["docs"]:
            id_exists[doc["_id"]] = doc.get("found")
        return id_exists

    def get_all_items_with_missing_field_count(self, index_name: str, missing_field: str) -> int:
        query = {"query": {"bool": {"must_not": {"exists": {"field": missing_field}}}}}
        response = self.client.count(index=index_name, body=query, ignore_unavailable=True)  # type: ignore
        return response["count"]

    def get_all_items_with_missing_field(
        self, index_name: str, missing_field: str, required_fields: list[str], internal_batch_size: int = 1000
    ) -> Generator:
        query = {"_source": required_fields, "query": {"bool": {"must_not": {"exists": {"field": missing_field}}}}}
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
            "script": {
                "source": f"ctx._source['{field}'] = null",  # setting it to null is supposedly more efficient than deleting it
            },
        }

        response = self.client.update_by_query(index=index_name, body=body)
        logging.warning(f"Deleted field {field} from text search engine: {response}")

    def get_plain_results(self, dataset: Dataset, query_body: dict) -> dict:
        # not used internally, mostly for external scripts
        index_name = dataset.actual_database_name
        response = self.client.search(body=query_body, index=index_name)
        return response

    def get_search_results(
        self,
        dataset: DotDict,
        search_fields,
        filters: list[dict],
        query_positive,
        query_negative,
        page,
        limit,
        return_fields,
        highlights=False,
        use_bolding_in_highlights: bool = True,
        highlight_query: str | None = None,
        ignored_highlight_fields: list | None = None,
        default_operator: str = "and",
        sort_settings: list | None = None,
        boost_function: dict | None = None,
    ) -> tuple[list, int]:
        if dataset.source_plugin == SourcePlugin.REMOTE_DATASET:
            return use_remote_db(
                dataset=dataset,
                db_type="text_search_engine",
                function_name="get_search_results",
                arguments={
                    "search_fields": search_fields,
                    "filters": filters,
                    "query_positive": query_positive,
                    "query_negative": query_negative,
                    "page": page,
                    "limit": limit,
                    "return_fields": return_fields,
                    "highlights": highlights,
                    "use_bolding_in_highlights": use_bolding_in_highlights,
                    "highlight_query": highlight_query,
                    "ignored_highlight_fields": ignored_highlight_fields,
                    "default_operator": default_operator,
                    "boost_function": boost_function,
                },
            )
        if filters:
            query = {
                "from": page * limit,
                "size": limit,
                "query": {
                    "bool": {
                        "filter": self._convert_to_opensearch_filters(filters),
                    }
                },
                "_source": return_fields,
            }
            if query_positive:
                query["query"]["bool"]["must"] = {
                    "simple_query_string": {
                        "query": self._convert_to_simple_query_language(query_positive),
                        "fields": search_fields,
                        "default_operator": default_operator,
                    }
                }
        elif query_positive:
            query = {
                "from": page * limit,
                "size": limit,
                "query": {
                    "simple_query_string": {
                        "query": self._convert_to_simple_query_language(query_positive),
                        "fields": search_fields,
                        "default_operator": default_operator,
                    }
                },
                "_source": return_fields,
            }
        else:
            query = {
                "from": page * limit,
                "size": limit,
                "query": {
                    "match_all": {},
                },
                "_source": return_fields,
            }
        if highlights:
            # profiling results: on a very fast SSD, getting 2k items with highlights takes about 360ms, without only 60ms
            highlight_fields = [field for field in search_fields if field not in (ignored_highlight_fields or [])]
            query["highlight"] = {
                "fields": {field: {} for field in highlight_fields},
                "number_of_fragments": 2,
                "order": "score",
                "pre_tags": ["<b>"] if use_bolding_in_highlights else [""],
                "post_tags": ["</b>"] if use_bolding_in_highlights else [""],
                "fragment_size": 400,
            }
            if highlight_query:
                query["highlight"]["highlight_query"] = {
                    "simple_query_string": {
                        "query": self._convert_to_simple_query_language(highlight_query),
                        "fields": highlight_fields,
                        "default_operator": "and",
                    }
                }
        if boost_function:
            query["query"] = {
                "function_score": {
                    "query": query["query"],
                    **boost_function,
                }
            }
        if sort_settings:
            query["sort"] = sort_settings
            query["track_scores"] = True

        logging.warning(f"Query: {json.dumps(query, indent=2)}")

        response = self.client.search(
            body=query,
            index=dataset.actual_database_name,
        )
        total_matches = response.get("hits", {}).get("total", {}).get("value", 0)
        return response.get("hits", {}).get("hits", []), total_matches

    def _convert_to_opensearch_filters(self, filters: list[dict]):
        query_filter = {
            "bool": {
                "must": [],
                "must_not": [],
            },
        }
        for filter_ in filters:
            filter_ = DotDict(filter_)
            if filter_.operator == "contains":
                if isinstance(filter_.field, list):
                    f = {"bool": {"should": []}}
                    for field in filter_.field:
                        f["bool"]["should"].append({"match_phrase": {field: filter_.value}})
                    query_filter["bool"]["must"].append(f)
                else:
                    query_filter["bool"]["must"].append({"match_phrase": {filter_.field: filter_.value}})
            elif filter_.operator == "does_not_contain":
                query_filter["bool"]["must_not"].append({"match_phrase": {filter_.field: filter_.value}})
            elif filter_.operator in ("is", "is_not"):
                # Note: also works to check if a given element is in an array of the document
                query_filter["bool"]["must" if filter_.operator == "is" else "must_not"].append(
                    {"term": {filter_.field: {"value": filter_.value, "case_insensitive": True}}}
                )
            elif filter_.operator in ("in", "not_in"):
                if filter_.field == "_id":
                    query_filter["bool"]["must"].append({"ids": {"values": filter_.value}})
                else:
                    # only works for keyword fields, not text fields
                    query_filter["bool"]["must" if filter_.operator == "in" else "must_not"].append(
                        {
                            "terms": {
                                filter_.field: filter_.value,
                            }
                        }
                    )
            elif filter_.operator == "is_empty":
                query_filter["bool"]["must"].append(
                    {
                        "bool": {
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": filter_.field}}]}},
                                {"term": {filter_.field: ""}},
                            ]
                        }
                    }
                )
            elif filter_.operator == "is_not_empty":
                query_filter["bool"]["must"].append({"exists": {"field": filter_.field}})
                query_filter["bool"]["must"].append({"bool": {"must_not": [{"term": {filter_.field: ""}}]}})
            elif filter_.operator in ("lt", "lte", "gt", "gte"):
                category = "must_not" if filter_.negate else "must"
                query_filter["bool"][category].append({"range": {filter_.field: {filter_.operator: filter_.value}}})
        return query_filter

    def _convert_to_simple_query_language(self, query: str):
        conversion = {"AND": "+", "OR": "|", r"NOT\s+": "-"}
        for old, new in conversion.items():
            query = re.sub(old, new, query)
        return query
