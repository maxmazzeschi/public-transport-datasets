import json
import os
import threading
from .dataset import Dataset
import re
import logging
import psutil
import gc
from contextlib import contextmanager

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

# Configure logger for this module
logger = logging.getLogger(__name__)

datasets = {}
dataset_being_created = {}
dataset_being_destroyed = {}
dataset_creation_events = {}
dataset_destruction_events = {}
datasets_lock = threading.Lock()

available_datasets = {}
available_datasets_lock = threading.Lock()

LOCK_DIR = os.path.join("/tmp", "public_transport_datasets_locks")


def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB


def _sanitize_lock_name(dataset_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", dataset_id)


@contextmanager
def _process_dataset_lock(dataset_id: str):
    """Serialize dataset lifecycle operations across gunicorn workers."""
    if fcntl is None:
        yield
        return

    os.makedirs(LOCK_DIR, exist_ok=True)
    lock_path = os.path.join(
        LOCK_DIR, f"{_sanitize_lock_name(dataset_id)}.lock"
    )
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


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
            if ds and not dataset_being_destroyed.get(id, False):
                return ds

        with _process_dataset_lock(id):
            while True:
                wait_event = None

                with datasets_lock:
                    if dataset_being_destroyed.get(id, False):
                        logger.debug(
                            "Dataset %s is being destroyed, waiting for "
                            "completion...",
                            id,
                        )
                        if id not in dataset_destruction_events:
                            dataset_destruction_events[id] = threading.Event()
                        wait_event = dataset_destruction_events[id]
                    else:
                        ds = datasets.get(id)
                        if ds:
                            return ds

                        if dataset_being_created.get(id, False):
                            logger.debug(
                                "Dataset %s is being created by another "
                                "thread, waiting...",
                                id,
                            )
                            if id not in dataset_creation_events:
                                dataset_creation_events[id] = threading.Event()
                            wait_event = dataset_creation_events[id]
                        else:
                            if id not in dataset_creation_events:
                                dataset_creation_events[id] = threading.Event()
                            dataset_creation_events[id].clear()
                            dataset_being_created[id] = True
                            break

                wait_event.wait()

            provider = DatasetsProvider.get_source_by_id(id)
            if provider is None:
                with datasets_lock:
                    dataset_being_created[id] = False
                    dataset_creation_events[id].set()
                return None

            logger.debug(f"Creating dataset for {id}")
            created_dataset = None
            try:
                created_dataset = Dataset(provider)
                with datasets_lock:
                    datasets[id] = created_dataset
                    logger.debug(f"Dataset {id} created")
                    return created_dataset
            finally:
                with datasets_lock:
                    dataset_being_created[id] = False
                    dataset_creation_events[id].set()

    @staticmethod
    def destroy_dataset(id):
        """Enhanced destruction with reference checking"""
        logger.debug(f"Destroying dataset {id} memory {get_memory_usage()}")

        with _process_dataset_lock(id):
            with datasets_lock:
                if id not in datasets:
                    logger.warning(f"Dataset {id} not found for destruction")
                    return

                dataset_being_destroyed[id] = True

                if id not in dataset_destruction_events:
                    dataset_destruction_events[id] = threading.Event()
                dataset_destruction_events[id].clear()

                ds = datasets[id]
                del datasets[id]

                logger.debug(f"Dataset {id} removed from active datasets")

            try:
                # Call explicit cleanup method
                if hasattr(ds, "cleanup"):
                    ds.cleanup()
                else:
                    # Fallback to manual cleanup if no cleanup method exists
                    if hasattr(ds, "vehicles"):
                        if hasattr(ds.vehicles, "stop"):
                            ds.vehicles.stop()

                        # Check if we're trying to join from the same thread
                        if (
                            hasattr(ds.vehicles, "update_thread")
                            and ds.vehicles.update_thread.is_alive()
                        ):
                            current_thread = threading.current_thread()
                            update_thread = ds.vehicles.update_thread

                            if current_thread != update_thread:
                                logger.debug(
                                    "Waiting for update thread to stop "
                                    "for dataset %s",
                                    id,
                                )
                                update_thread.join(timeout=10)

                    # Manual cleanup of trip_last_stops
                    if (
                        hasattr(ds, "trip_last_stops")
                        and ds.trip_last_stops is not None
                    ):
                        ds.trip_last_stops.clear()
                        ds.trip_last_stops = None

                    if hasattr(ds, "gdf"):
                        ds.gdf = None

                # Check reference count after cleanup
                import sys

                ref_count = sys.getrefcount(ds)
                logger.debug(
                    "Dataset %s reference count after cleanup: %s",
                    id,
                    ref_count,
                )

                # Force deletion
                del ds

                # Multiple garbage collection passes
                for i in range(3):
                    collected = gc.collect()
                    logger.debug(
                        "GC pass %s: collected %s objects", i + 1, collected
                    )

            except Exception as e:
                logger.error(f"Error during dataset {id} destruction: {e}")

            finally:
                with datasets_lock:
                    dataset_being_destroyed[id] = False

                    if id in dataset_destruction_events:
                        dataset_destruction_events[id].set()

                    logger.debug(f"Dataset {id} destruction completed")
                    logger.debug(
                        "destruction dataset %s completed memory %s",
                        id,
                        get_memory_usage(),
                    )

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
                                        if auth_type != 0:
                                            api_key_env_var = provider.get(
                                                (
                                                    "vehicle_positions_"
                                                    "url_api_key_env_var"
                                                ),
                                                None,
                                            )
                                            if (
                                                api_key_env_var is None
                                                or api_key_env_var == ""
                                            ):
                                                # Skip provider if env var is
                                                # missing.
                                                continue
                                            api_key = os.getenv(
                                                api_key_env_var
                                            )
                                            if api_key is None:
                                                # Skip provider if API key is
                                                # not set.
                                                continue
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
            return list(unique_countries)

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
