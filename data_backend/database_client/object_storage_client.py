import logging
from typing import Iterable
from uuid import UUID
import os

from bson import UuidRepresentation
from bson.errors import InvalidDocument

from pymongo import MongoClient, ReplaceOne, UpdateOne
from pymongo.errors import BulkWriteError

from utils.dotdict import DotDict


# docker run --name mongo --rm -p 27017:27017 mongodb/mongodb-community-server:latest

mongo_host = os.getenv("object_storage_host", "localhost")
mongo_port = 27017
mongo_db_name = "visual_data_map"


class ObjectStorageEngineClient(object):

    # using a singleton here to have only one DB connection, but lazy-load it only when used to speed up startup time
    _instance: "ObjectStorageEngineClient" = None # type: ignore


    def __init__(self):
        self.client = MongoClient(mongo_host, mongo_port, uuidRepresentation='standard')
        self.db = self.client[mongo_db_name]


    @staticmethod
    def get_instance() -> "ObjectStorageEngineClient":
        if ObjectStorageEngineClient._instance is None:
            ObjectStorageEngineClient._instance = ObjectStorageEngineClient()
        return ObjectStorageEngineClient._instance


    def get_collection(self, schema_id: int):
        return get_collection_with_numpy_support(f'schema_{schema_id}', self.db)


    def ensure_schema_exists(self, schema: dict):
        schema = DotDict(schema)
        collection = self.get_collection(schema.id)
        # TODO: create indexes
        # collection.create_index(fieldname)
        # but are indexes for object storage beside id actually necessary?
        pass


    def remove_schema(self, schema_id: int):
        collection = self.get_collection(schema_id)
        collection.drop()


    def upsert_items(self, schema_id: int, batch: list[dict]):
        collection = self.get_collection(schema_id)
        requests = []
        for item in batch:
            # TODO: check if UUID hex string should be converted to BSON UUID value for better performance
            requests.append(ReplaceOne({"_id": item["_id"]}, item, upsert=True))
        try:
            collection.bulk_write(requests, ordered=False)
        except BulkWriteError as bwe:
            logging.error(bwe.details)
        except InvalidDocument as error:
            # FIXME: this can happen when a key is None, but the document should still be inserted then
            logging.error(error)
            logging.error(error.args)


    def remove_items(self, schema_id: int, ids: list[UUID]):
        collection = self.get_collection(schema_id)
        collection.delete_many({"_id": {"$in": ids}})


    def get_items_by_ids(self, schema_id: int, ids: Iterable[UUID], fields: list[str]) -> list:
        collection = self.get_collection(schema_id)
        result = collection.find(filter={"_id": {"$in": list(ids)}}, projection=fields)
        return list(result)


    def get_all_items_with_missing_field_count(self, schema_id, missing_field) -> int:
        collection = self.get_collection(schema_id)
        result = collection.count_documents(filter={missing_field: None})
        return result


    def get_all_items_with_missing_field(self, schema_id, missing_field, limit, offset) -> list[dict]:
        collection = self.get_collection(schema_id)
        result = collection.find(filter={missing_field: None})
        return list(result.skip(offset).limit(limit))


    def clear_field(self, schema_id, field):
        collection = self.get_collection(schema_id)
        collection.update({}, {"$set": {field: None}})


# add support for numpy ndarrays to Mongo:
# see here: https://stackoverflow.com/a/66410481

import pickle
from bson.binary import Binary, USER_DEFINED_SUBTYPE
from bson.codec_options import TypeCodec, TypeRegistry, CodecOptions
import numpy as np


class NumpyCodec(TypeCodec):
    python_type = np.ndarray # type: ignore
    bson_type = Binary # type: ignore

    def transform_python(self, value):
        return Binary(pickle.dumps(value, protocol=2), USER_DEFINED_SUBTYPE)

    def transform_bson(self, value):
        if value.subtype == USER_DEFINED_SUBTYPE:
            return pickle.loads(value)
        return value

def get_codec_options():
    numpy_codec = NumpyCodec()
    type_registry = TypeRegistry([numpy_codec])
    codec_options = CodecOptions(type_registry=type_registry, uuid_representation=UuidRepresentation.STANDARD)
    return codec_options

def get_collection_with_numpy_support(name, db):
    codec_options = get_codec_options()
    return db.get_collection(name, codec_options=codec_options)

