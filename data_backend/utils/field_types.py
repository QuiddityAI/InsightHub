
# Note: also update organization_backend/data_map_backend/models.py -> FieldType


class FieldType():
    TEXT = "TEXT"
    IDENTIFIER = "IDENTIFIER"
    FLOAT = "FLOAT"
    INTEGER = "INTEGER"
    DATE = "DATE"
    DATETIME = "DATETIME"
    TIME = "TIME"
    VECTOR = "VECTOR"
    CLASS_PROBABILITY = "CLASS_PROBABILITY"  # single: class -> score, array: dict of classes and scores
    FACE = "FACE"
    URL = "URL"
    GEO_COORDINATES = "GEO_COORDINATES"
    TAG = "TAG"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    FOREIGN_KEY = "FOREIGN_KEY"
    BOOL = "BOOL"
    ATTRIBUTES = "ATTRIBUTES"  # dict of attribute name -> attribute value, used for facets, attributes can be different per item but each is indexed
    ARBITRARY_OBJECT = "ARBITRARY_OBJECT"  # object that has arbritrary keys, won't be indexed per key
