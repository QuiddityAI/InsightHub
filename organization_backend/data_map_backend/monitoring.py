from prometheus_client.core import StateSetMetricFamily, REGISTRY
from prometheus_client.registry import Collector

from .data_backend_client import get_data_backend_health, get_data_backend_database_health


class DataBackendStatusCollector(Collector):
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


REGISTRY.register(DataBackendStatusCollector())
