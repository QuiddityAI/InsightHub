


typesense_host = "http://localhost:55202"


class TextSearchEngineClient(object):

    # using a singleton here to have only one DB connection, but lazy-load it only when used to speed up startup time
    _instance: "TextSearchEngineClient"


    def __init__(self):
        pass


    @staticmethod
    def get_instance() -> "TextSearchEngineClient":
        if TextSearchEngineClient._instance is None:
            TextSearchEngineClient._instance = TextSearchEngineClient()
        return TextSearchEngineClient._instance


    def ensure_schema_exists(self, schema: dict):
        # create schema
        # create indexes
        # check if schema is still valid, update if necessary
        pass


    def remove_schema(self, schema_id: str):
        pass


    def upsert_items(self, schema_id: str, batch: list[dict]):
        pass


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
