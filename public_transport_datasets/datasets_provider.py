import json
import os
import threading
from .dataset import Dataset
import re

datasets = {}
datasets_lock = threading.Lock()

available_datasets = {}
available_datasets_lock = threading.Lock()


class DatasetsProvider:
    def __init__(self, id):
        pass

    @staticmethod
    def get_config_path():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(
            os.path.join(os.path.join(base_dir, "providers"), "GTFS")
        )
        return config_path

    @staticmethod
    def get_dataset(id):
        print(f"dataset {id} requested")
        DatasetsProvider.load_sources()
        with datasets_lock:
            ds = datasets.get(id)
            if ds:
                return ds
            provider = DatasetsProvider.get_source_by_id(id)
            if provider is None:
                return None
            ds = Dataset(provider)
            datasets[id] = ds
            return ds

    @staticmethod
    def load_sources():
        with available_datasets_lock:
            if available_datasets == {}:
                config_path = DatasetsProvider.get_config_path()
                with os.scandir(config_path) as file_list:
                    for entry in file_list:
                        if re.search(r"\.json", os.fsdecode(entry.name)):
                            try:
                                with open(entry.path) as f:
                                    provider = json.load(f)
                                    provider_hash = provider["id"]
                                    available_datasets[
                                        provider_hash
                                    ] = provider
                            except Exception as ex:
                                print(f"Error {ex} {entry.name}")

    @staticmethod
    def get_source_by_id(id: str):
        with available_datasets_lock:
            return available_datasets.get(id, None)

    @staticmethod
    def get_available_countries() -> list:
        DatasetsProvider.load_sources()
        print(f"available_datasets count {len(available_datasets)}")
        with available_datasets_lock:
            unique_countries = {
                data["country"]
                for data in available_datasets.values()
                if data.get("enabled", False)
            }
            return unique_countries

    @staticmethod
    def get_datasets_by_country(country: str) -> list:
        DatasetsProvider.load_sources()
        with available_datasets_lock:
            return [
                {"id": k, "name": v["city"]}
                for k, v in available_datasets.items()
                if v["country"] == country
            ]

    @staticmethod
    def get_all_datasets():
        DatasetsProvider.load_sources()
        return available_datasets
