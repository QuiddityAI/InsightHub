import logging
import os

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, PayloadSchemaType, NamedVector
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


    def _get_collection_name(self, schema_id: int, vector_field: str):
        return f'schema_{schema_id}_field_{vector_field}'


    def ensure_schema_exists(self, schema: dict, vector_field: str, update_params: bool = False, delete_if_params_changed: bool = False):
        schema = DotDict(schema)
        vector_configs = {}
        vector_configs_update = {}
        field = schema.object_fields[vector_field]
        if not (field.is_available_for_search and field.field_type == FieldType.VECTOR and not field.is_array):
            logging.error(f"Field is not supposed to be indexed or isn't a single vector: {field.identifier}")
            raise ValueError(f"Field is not supposed to be indexed or isn't a single vector: {field.identifier}")
        vector_size = get_vector_field_dimensions(field)
        if not vector_size:
            logging.error(f"Indexed vector field doesn't have vector size: {field.identifier}")
            raise ValueError(f"Indexed vector field doesn't have vector size: {field.identifier}")
        logging.info(f"Creating vector field {field.identifier} with size {vector_size}")
        vector_configs[field.identifier] = models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
        vector_configs_update[field.identifier] = models.VectorParamsDiff()  # TODO: add params
        # TODO: parse and add field.index_parameters for HNSW, storage type, quantization etc.

        collection_name = self._get_collection_name(schema.id, vector_field)

        try:
            self.client.get_collection(collection_name)
        except UnexpectedResponse as e:
            if e.status_code != 404:
                raise e
            # status code is 404 -> collection doesn't exist yet
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=vector_configs,
            )
        else:
            if delete_if_params_changed:
                self.client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=vector_configs,
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
        for field in schema.object_fields.values():
            if not field.is_available_for_filtering:
                continue
            if field.field_type not in indexable_field_type_to_qdrant_type:
                continue
            if field.is_array and field.field_type != FieldType.TAG:
                logging.warning("Array fields are not yet supported for indexing in Qdrant, must be flattened somehow")
                continue

            logging.info(f"Creating indexed payload field {field.identifier} with type {field.field_type}")
            self.client.create_payload_index(collection_name=collection_name,
                field_name=field.identifier,
                field_schema=indexable_field_type_to_qdrant_type[field.field_type])


    def delete_field(self, schema_id: int, vector_field: str):
        try:
            self.client.delete_collection(self._get_collection_name(schema_id, vector_field))
        except Exception as e:
            print(e)


    def upsert_items(self, schema_id: int, vector_field: str, ids: list, payloads: list[dict], vectors: list):
        collection_name = self._get_collection_name(schema_id, vector_field)

        self.client.upsert(
            collection_name=collection_name,
            points=models.Batch(ids=ids, payloads=payloads, vectors={vector_field: vectors}),
        )


    def remove_items(self, schema_id: int, vector_field: str, ids: list):
        collection_name = self._get_collection_name(schema_id, vector_field)
        self.client.delete(collection_name, ids)


    def get_items_near_vector(self, schema_id: int, vector_field: str, query_vector: list,
                              filter_criteria: dict, return_vectors: bool, limit: int,
                              score_threshold: float | None) -> list:
        hits = self.client.search(
            collection_name=self._get_collection_name(schema_id, vector_field),
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
        return hits


    def get_items_matching_collection(self, schema_id: int, vector_field: str, positive_ids: list[str],
                                      negative_ids: list[str], filter_criteria: dict, return_vectors: bool,
                                      limit: int, score_threshold: float | None) -> list:
        hits = self.client.recommend(
            collection_name=self._get_collection_name(schema_id, vector_field),
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
        return hits


    def get_items_by_primary_keys(self, schema_id: str, primary_key_field: str,
                                  item_pks: list[str], fields: list[str]) -> list[dict]:
        # is this needed?
        return []


