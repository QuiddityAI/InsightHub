import logging
import os
from typing import Iterable, List
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, PayloadSchemaType, NamedVector, HnswConfigDiff
from qdrant_client.http.exceptions import UnexpectedResponse

from utils.dotdict import DotDict
from utils.field_types import FieldType
from utils.helpers import get_vector_field_dimensions


qdrant_host = os.getenv("vector_database_host", "localhost")
qdrant_port = 6333

# docker run --name qdrant --rm -p 6333:6333 qdrant/qdrant:latest
# then see http://localhost:55201/dashboard


class VectorSearchEngineClient(object):

    # using a singleton here to have only one DB connection, but lazy-load it only when used to speed up startup time
    _instance: "VectorSearchEngineClient" = None # type: ignore


    def __init__(self):
        self.client = QdrantClient(qdrant_host, port=qdrant_port)  # , grpc_port=6334, prefer_grpc=True
        # self.client = QdrantClient(":memory:")


    @staticmethod
    def get_instance() -> "VectorSearchEngineClient":
        if VectorSearchEngineClient._instance is None:
            VectorSearchEngineClient._instance = VectorSearchEngineClient()
        return VectorSearchEngineClient._instance


    def _get_collection_name(self, database_name: str, vector_field: str):
        return f'{database_name}_field_{vector_field}'


    def ensure_dataset_field_exists(self, dataset: dict, vector_field: str, update_params: bool = False, delete_if_params_changed: bool = False):
        dataset = DotDict(dataset)
        field = dataset.object_fields[vector_field]
        if not (field.is_available_for_search and field.field_type == FieldType.VECTOR):
            logging.error(f"Field is not supposed to be indexed: {field.identifier}")
            raise ValueError(f"Field is not supposed to be indexed: {field.identifier}")
        vector_size = get_vector_field_dimensions(field)
        if not vector_size:
            logging.error(f"Indexed vector field doesn't have vector size: {field.identifier}")
            raise ValueError(f"Indexed vector field doesn't have vector size: {field.identifier}")
        logging.info(f"Creating vector field {field.identifier} with size {vector_size}")
        vector_configs = {}
        vector_configs[field.identifier] = models.VectorParams(size=vector_size, distance=models.Distance.COSINE,
                                                               on_disk=True, hnsw_config=HnswConfigDiff(on_disk=True))
        vector_configs_update = {}
        vector_configs_update[field.identifier] = models.VectorParamsDiff(on_disk=True, hnsw_config=HnswConfigDiff(on_disk=True))  # TODO: add params
        # TODO: parse and add field.index_parameters for HNSW, storage type, quantization etc.

        collection_name = self._get_collection_name(dataset.actual_database_name, vector_field)
        if field.is_array:
            collection_name = f'{collection_name}_sub_items'

        try:
            self.client.get_collection(collection_name)
        except UnexpectedResponse as e:
            if e.status_code != 404:
                raise e
            # status code is 404 -> collection doesn't exist yet
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=vector_configs,
                on_disk_payload=True,  # TODO: this might make filtering slow
            )
        else:
            if delete_if_params_changed:
                self.client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=vector_configs,
                    on_disk_payload=True,  # TODO: this might make filtering slow
                )
            elif update_params:
                self.client.update_collection(
                    collection_name=collection_name,
                    vectors_config=vector_configs_update,
                )

        indexable_field_type_to_qdrant_type = {
            FieldType.TEXT: PayloadSchemaType.TEXT,  # TODO: fulltext indexes can have special parameters
            FieldType.TAG: PayloadSchemaType.KEYWORD,  # TODO: check if this works
            FieldType.INTEGER: PayloadSchemaType.INTEGER,
            FieldType.FLOAT: PayloadSchemaType.FLOAT,
            FieldType.BOOL: PayloadSchemaType.BOOL,
            FieldType.GEO_COORDINATES: PayloadSchemaType.GEO,  # FIXME: might need conversion
        }

        # create payload indexes:
        for other_field in dataset.object_fields.values():
            if not other_field.is_available_for_filtering:
                continue
            if other_field.field_type not in indexable_field_type_to_qdrant_type:
                continue
            if other_field.is_array and other_field.field_type != FieldType.TAG:
                logging.warning("Array fields are not yet supported for indexing in Qdrant, must be flattened somehow")
                continue

            logging.warning(f"Creating indexed payload field {other_field.identifier} with type {other_field.field_type}")
            self.client.create_payload_index(collection_name=collection_name,
                field_name=other_field.identifier,
                field_schema=indexable_field_type_to_qdrant_type[other_field.field_type])

        if field.is_array:
            logging.warning(f"Creating payload index for parent_id field because this is an array field with sub-items")
            self.client.create_payload_index(collection_name=collection_name,
                field_name='parent_id',
                field_schema=PayloadSchemaType.KEYWORD)

            # create a separate collection for the parent item data, for 'lookups':
            lookup_collection_name = self._get_collection_name(dataset.actual_database_name, vector_field)
            try:
                self.client.get_collection(lookup_collection_name)
            except UnexpectedResponse as e:
                if e.status_code != 404:
                    raise e
                # status code is 404 -> collection doesn't exist yet
                lookup_vector_configs = {}
                lookup_vector_configs[field.identifier] = models.VectorParams(size=1, distance=models.Distance.COSINE,
                                                                    on_disk=True, hnsw_config=HnswConfigDiff(on_disk=True))
                self.client.create_collection(
                    collection_name=lookup_collection_name,
                    vectors_config=lookup_vector_configs,
                    on_disk_payload=True,  # TODO: this might make filtering slow
                )


    def delete_field(self, database_name: str, vector_field: str, is_array_field: bool):
        collection_name = self._get_collection_name(database_name, vector_field)
        try:
            self.client.delete_collection(collection_name)
        except Exception as e:
            print(e)
        if is_array_field:
            try:
                self.client.delete_collection(f'{collection_name}_sub_items')
            except Exception as e:
                print(e)


    def get_item_count(self, database_name: str, vector_field: str, count_sub_items_of_array_field: bool = False) -> int:
        collection_name = self._get_collection_name(database_name, vector_field)
        if count_sub_items_of_array_field:
            collection_name = f'{collection_name}_sub_items'
        try:
            return self.client.count(collection_name).count
        except Exception as e:
            logging.warning(e)
            return 0


    def upsert_items(self, database_name: str, vector_field: str, ids: list, payloads: list[dict], vectors: list):
        collection_name = self._get_collection_name(database_name, vector_field)
        is_array_of_vectors = isinstance(vectors[0][0], Iterable)
        if is_array_of_vectors:
            # if an array vector field is changed that existed before, we can't just override it
            # but need to delete all sub points before adding the new ones as there might be less new ones
            self.client.delete(
                collection_name=f'{collection_name}_sub_items',
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="parent_id",
                                match=models.MatchAny(any=ids)
                            ),
                        ],
                    )
                ),
            )
            sub_item_ids = []
            sub_item_vectors = []
            sub_item_payloads = []
            for item_id, payload, vector_array in zip(ids, payloads, vectors):
                for i, vector in enumerate(vector_array):
                    sub_item_payload = payload.copy()
                    sub_item_payload['parent_id'] = item_id
                    sub_item_payload['array_index'] = i
                    sub_item_payloads.append(sub_item_payload)
                    sub_item_id = f"{item_id}_{i}"
                    sub_item_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, sub_item_id))
                    sub_item_ids.append(sub_item_uuid)
                    sub_item_vectors.append(vector)

            # do in batches of 1024, otherwise it might time out:
            for i in range(0, len(sub_item_ids), 1024):
                self.client.upsert(
                    collection_name=f'{collection_name}_sub_items',
                    points=models.Batch(ids=sub_item_ids[i:i+1024], payloads=sub_item_payloads[i:i+1024], vectors={vector_field: sub_item_vectors[i:i+1024]}),
                )
            # create empty payloads and vectors for the lookup collection:
            payloads = [{} for _ in ids]
            vectors = [[0] for _ in ids]
            # fall through to normal behavior for the parent items

        self.client.upsert(
            collection_name=collection_name,
            points=models.Batch(ids=ids, payloads=payloads, vectors={vector_field: vectors}),
        )


    def remove_items(self, database_name: str, vector_field: str, ids: list, is_array_field: bool):
        collection_name = self._get_collection_name(database_name, vector_field)
        self.client.delete(collection_name, ids)
        if is_array_field:
            self.client.delete(
                collection_name=f'{collection_name}_sub_items',
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="parent_id",
                                match=models.MatchAny(any=ids)
                            ),
                        ],
                    )
                ),
            )


    def get_items_near_vector(self, database_name: str, vector_field: str, query_vector: list,
                              filter_criteria: dict, return_vectors: bool, limit: int,
                              score_threshold: float | None, min_results: int = 10, is_array_field: bool=False, max_sub_items: int = 1) -> list:
        collection_name = self._get_collection_name(database_name, vector_field)
        if is_array_field:
            group_hits = self.client.search_groups(
                collection_name=f'{collection_name}_sub_items',
                query_vector=NamedVector(name=vector_field, vector=query_vector),
                with_payload=['array_index'],
                with_vectors=return_vectors,
                limit=limit,
                score_threshold=score_threshold,
                group_by='parent_id',
                group_size=max_sub_items,
            )
            # hits.groups is a list of {'id': parent_id, 'hits': [{'id': sub_id, 'score': score, 'payload': dict} ...]}
            hits = []
            for group in group_hits.groups:
                hits.append(DotDict({
                    'id': group.id,
                    'score': group.hits[0].score,
                    'array_index': group.hits[0].payload['array_index']  # type: ignore
                }))
            if min_results > 0 and len(hits) < min_results and score_threshold:
                # try again without score threshold
                return self.get_items_near_vector(database_name, vector_field, query_vector, filter_criteria, return_vectors, min(min_results, limit), None, min_results, is_array_field, max_sub_items)
            return hits  # type: ignore

        hits = self.client.search(
            collection_name=collection_name,
            query_vector=NamedVector(name=vector_field, vector=query_vector),
            # query_filter=Filter(
            #     must=[
            #         FieldCondition(
            #             key='rand_number',
            #             range=Range(
            #                 gte=3
            #             )
            #         )
            #     ]
            # ),
            with_payload=False,
            with_vectors=return_vectors,
            limit=limit,
            score_threshold=score_threshold,
        )
        if min_results > 0 and len(hits) < min_results and score_threshold:
            # try again without score threshold
            return self.get_items_near_vector(database_name, vector_field, query_vector, filter_criteria, return_vectors, min(min_results, limit), None, min_results, is_array_field, max_sub_items)
        return hits


    def get_items_matching_collection(self, database_name: str, vector_field: str, positive_ids: list[str],
                                      negative_ids: list[str], filter_criteria: dict, return_vectors: bool,
                                      limit: int, score_threshold: float | None, min_results: int = 10) -> list:
        hits = self.client.recommend(
            collection_name=self._get_collection_name(database_name, vector_field),
            positive=positive_ids,
            negative=negative_ids,
            using=vector_field,
            # query_filter=Filter(
            #     must=[
            #         FieldCondition(
            #             key='rand_number',
            #             range=Range(
            #                 gte=3
            #             )
            #         )
            #     ]
            # ),
            with_payload=False,
            with_vectors=return_vectors,
            limit=limit,
            score_threshold=score_threshold,
        )
        if len(hits) == 0 and score_threshold and min_results > 0:
            return self.get_items_matching_collection(database_name, vector_field, positive_ids, negative_ids, filter_criteria, return_vectors, min(min_results, limit), None, min_results)
        return hits


    def get_items_by_ids(self, database_name: str, ids: List[str], vector_field: str, is_array_field: bool,
                         return_vectors: bool = False, return_payloads: bool = False) -> list:
        if is_array_field and return_vectors:
            logging.warning("Returning vectors for array fields is not supported yet")
            # TODO: return sub-items vectors by iterating over ids and fetch vectors for each parent item
        hits = self.client.retrieve(
            collection_name=self._get_collection_name(database_name, vector_field),
            ids=ids, # type: ignore
            with_payload=return_payloads,
            with_vectors=return_vectors
        )
        return hits
