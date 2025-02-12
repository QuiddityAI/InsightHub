import logging

from prometheus_client.core import REGISTRY, GaugeMetricFamily, StateSetMetricFamily
from prometheus_client.registry import Collector

from legacy_backend.database_client.text_search_engine_client import (
    TextSearchEngineClient,
)
from legacy_backend.database_client.vector_search_engine_client import (
    VectorSearchEngineClient,
)


def get_db_health():
    try:
        text_search_engine_client = TextSearchEngineClient()
        if not text_search_engine_client.check_status():
            raise Exception("Text search engine not healthy")
        vector_search_engine_client = VectorSearchEngineClient()
        if not vector_search_engine_client.check_status():
            raise Exception("Vector search engine not healthy")
    except Exception as e:
        logging.error("Error checking database status", exc_info=True)
        return False
    return True


class DataBackendStatusCollector(Collector):
    def describe(self):
        # describe metrics here without using the database (as using the database is not allowed during startup of Django)
        yield GaugeMetricFamily("data_backend_status", "Status of the data_backend")
        yield GaugeMetricFamily("data_backend_database_status", "Status of the data_backend databases")

    def collect(self):
        data_backend_status = StateSetMetricFamily("data_backend_status", "Status of the data_backend")
        data_backend_database_status = StateSetMetricFamily(
            "data_backend_database_status", "Status of the data_backend databases"
        )
        # old metric from when backend was split into two parts:
        data_backend_status.add_metric([], {"healthy": True})
        yield data_backend_status
        if get_db_health():
            data_backend_database_status.add_metric([], {"healthy": True})
        else:
            data_backend_database_status.add_metric([], {"healthy": False})
        yield data_backend_database_status


class UserCountCollector(Collector):
    def describe(self):
        yield GaugeMetricFamily("user_count", "Number of users in the system")

    def collect(self):
        from .models import User

        user_count = GaugeMetricFamily("user_count", "Number of users in the system")
        user_count.add_metric([], User.objects.count())
        yield user_count


class UsageStatisticsCollector(Collector):
    def describe(self):
        yield GaugeMetricFamily("search_count", "Number of searches in the system")
        yield GaugeMetricFamily("dataset_count", "Number of datasets in the system")
        yield GaugeMetricFamily("collection_count", "Number of collections in the system")
        yield GaugeMetricFamily("collection_item_count", "Number of items in collections in the system")

    def collect(self):
        from .models import CollectionItem, DataCollection, Dataset, SearchHistoryItem

        search_count = GaugeMetricFamily("search_count", "Number of searches in the system")
        search_count.add_metric([], SearchHistoryItem.objects.count())
        yield search_count
        dataset_count = GaugeMetricFamily("dataset_count", "Number of datasets in the system")
        dataset_count.add_metric([], Dataset.objects.count())
        yield dataset_count
        collection_count = GaugeMetricFamily("collection_count", "Number of collections in the system")
        collection_count.add_metric([], DataCollection.objects.count())
        yield collection_count
        collection_item_count = GaugeMetricFamily(
            "collection_item_count", "Number of items in collections in the system"
        )
        collection_item_count.add_metric([], CollectionItem.objects.count())
        yield collection_item_count


def register_collectors():
    REGISTRY.register(DataBackendStatusCollector())
    REGISTRY.register(UserCountCollector())
    REGISTRY.register(UsageStatisticsCollector())
