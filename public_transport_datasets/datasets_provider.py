import json
import os
import threading
from .dataset import Dataset
import re
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

datasets = {}
dataset_being_created = {}
dataset_creation_events = {}  # Add this new dictionary
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
        logger.debug(f"dataset {id} requested")
        DatasetsProvider.load_sources()
        with datasets_lock:
            ds = datasets.get(id)
            if ds:
                return ds

            # Check if dataset is being created by another thread
            if id in dataset_being_created and dataset_being_created[id]:
                logger.debug(
                    f"Dataset {id} is being created by another thread, waiting..."
                )
                # Create or get the event for this dataset
                if id not in dataset_creation_events:
                    dataset_creation_events[id] = threading.Event()
                event = dataset_creation_events[id]

                # Release the lock while waiting
                datasets_lock.release()
                event.wait()  # Wait for the signal
                datasets_lock.acquire()

                # After waiting, check if dataset was created
                ds = datasets.get(id)
                if ds:
                    return ds

            provider = DatasetsProvider.get_source_by_id(id)
            if provider is None:
                return None

            # Create event for this dataset if it doesn't exist
            if id not in dataset_creation_events:
                dataset_creation_events[id] = threading.Event()

            dataset_being_created[id] = True
            logger.debug(f"Creating dataset for {id}")
            ds = Dataset(provider)
            datasets[id] = ds
            dataset_being_created[id] = False
            logger.debug(f"Dataset {id} created")

            # Signal waiting threads that dataset creation is complete
            dataset_creation_events[id].set()

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
                                    auth_type = provider.get(
                                        "authentication_type", None
                                    )
                                    if auth_type is not None:
                                        provider_hash = (
                                            f"{provider_hash}_{auth_type}"
                                        )
                                        if auth_type != 0:
                                            api_key_env_var = provider.get(
                                                "vehicle_positions_url_api_key_env_var",
                                                None,
                                            )
                                            if (
                                                api_key_env_var is None
                                                or api_key_env_var == ""
                                            ):
                                                continue  # Skip this provider if API key env var is not set
                                            api_key = os.getenv(
                                                api_key_env_var
                                            )
                                            if api_key is None:
                                                continue  # Skip this provider if API key is not set
                                        available_datasets[
                                            provider_hash
                                        ] = provider
                            except Exception as ex:
                                logger.error(f"Error {ex} {entry.name}")

    @staticmethod
    def get_source_by_id(id: str):
        with available_datasets_lock:
            return available_datasets.get(id, None)

    @staticmethod
    def get_available_countries() -> list:
        DatasetsProvider.load_sources()
        logger.debug(f"available_datasets count {len(available_datasets)}")
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
