from prometheus_client.core import StateSetMetricFamily, GaugeMetricFamily, REGISTRY
from prometheus_client.registry import Collector

from .data_backend_client import get_data_backend_health, get_data_backend_database_health


class DataBackendStatusCollector(Collector):

    def describe(self):
        # describe metrics here without using the database (as using the database is not allowed during startup of Django)
        yield GaugeMetricFamily('data_backend_status', 'Status of the data_backend')
        yield GaugeMetricFamily('data_backend_database_status', 'Status of the data_backend databases')

    def collect(self):
        data_backend_status = StateSetMetricFamily('data_backend_status', 'Status of the data_backend')
        data_backend_database_status = StateSetMetricFamily('data_backend_database_status', 'Status of the data_backend databases')
        if get_data_backend_health():
            data_backend_status.add_metric([], {'healthy': True})
        else:
            data_backend_status.add_metric([], {'healthy': False})
        yield data_backend_status
        if get_data_backend_database_health():
            data_backend_database_status.add_metric([], {'healthy': True})
        else:
            data_backend_database_status.add_metric([], {'healthy': False})
        yield data_backend_database_status


class UserCountCollector(Collector):

    def describe(self):
        yield GaugeMetricFamily('user_count', 'Number of users in the system')

    def collect(self):
        from .models import User
        user_count = GaugeMetricFamily('user_count', 'Number of users in the system')
        user_count.add_metric([], User.objects.count())
        yield user_count


class UsageStatisticsCollector(Collector):

    def describe(self):
        yield GaugeMetricFamily('search_count', 'Number of searches in the system')
        yield GaugeMetricFamily('dataset_count', 'Number of datasets in the system')
        yield GaugeMetricFamily('collection_count', 'Number of collections in the system')
        yield GaugeMetricFamily('collection_item_count', 'Number of items in collections in the system')

    def collect(self):
        from .models import SearchHistoryItem, DataCollection, Dataset, CollectionItem
        search_count = GaugeMetricFamily('search_count', 'Number of searches in the system')
        search_count.add_metric([], SearchHistoryItem.objects.count())
        yield search_count
        dataset_count = GaugeMetricFamily('dataset_count', 'Number of datasets in the system')
        dataset_count.add_metric([], Dataset.objects.count())
        yield dataset_count
        collection_count = GaugeMetricFamily('collection_count', 'Number of collections in the system')
        collection_count.add_metric([], DataCollection.objects.count())
        yield collection_count
        collection_item_count = GaugeMetricFamily('collection_item_count', 'Number of items in collections in the system')
        collection_item_count.add_metric([], CollectionItem.objects.count())
        yield collection_item_count


def register_collectors():
    REGISTRY.register(DataBackendStatusCollector())
    REGISTRY.register(UserCountCollector())
    REGISTRY.register(UsageStatisticsCollector())
