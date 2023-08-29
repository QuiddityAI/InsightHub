import logging

from pymongo import MongoClient, ReplaceOne, UpdateOne
from pymongo.errors import BulkWriteError

from utils.dotdict import DotDict


# docker run --name mongo mongodb/mongodb-community-server:latest

mongo_host = "localhost"
mongo_port = 27017
mongo_db_name = "visual_data_map"


class ObjectStorageEngineClient(object):

    # using a singleton here to have only one DB connection, but lazy-load it only when used to speed up startup time
    _instance: "ObjectStorageEngineClient"


    def __init__(self):
        self.client = MongoClient(mongo_host, mongo_port)
        self.db = self.client[mongo_db_name]


    @staticmethod
    def get_instance() -> "ObjectStorageEngineClient":
        if ObjectStorageEngineClient._instance is None:
            ObjectStorageEngineClient._instance = ObjectStorageEngineClient()
        return ObjectStorageEngineClient._instance


    def get_collection(self, schema_id: int):
        return self.db[f'schema_{schema_id}']


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
            requests.append(ReplaceOne({"_id": item["id"]}, item))
        try:
            collection.bulk_write(requests, ordered=False)
        except BulkWriteError as bwe:
            logging.error(bwe.details)


    def remove_items(self, schema_id: int, ids: list[str]):
        collection = self.get_collection(schema_id)
        collection.delete_many({"_id": {"$in": ids}})


    def get_items_by_primary_keys(self, schema_id: int, ids: list[str], fields: list[str]) -> list:
        collection = self.get_collection(schema_id)
        result = collection.find(filter={"_id": {"$in": ids}}, projection=fields)
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
