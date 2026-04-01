import logging
import os
import random
import sys
import threading
import time
import traceback
from multiprocessing import get_context

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


FAKE_PROVIDER = {
    "id": "stress-test-dataset",
    "country": "XX",
    "city": "Stress City",
    "vehicle_positions_url": "",
    "vehicle_positions_url_type": "GTFS-Realtime",
    "refresh_interval": 1,
}


def _install_test_doubles():
    from public_transport_datasets import datasets_provider as dp

    logging.getLogger("public_transport_datasets.datasets_provider").setLevel(
        logging.ERROR
    )

    class FakeDataset:
        def __init__(self, provider):
            self.src = provider
            time.sleep(0.001)

        def cleanup(self):
            time.sleep(0.001)

    dp.Dataset = FakeDataset

    def _fake_source_by_id(id):
        if id == FAKE_PROVIDER["id"]:
            return FAKE_PROVIDER
        return None

    dp.DatasetsProvider.get_source_by_id = staticmethod(_fake_source_by_id)
    return dp


def _thread_worker(
    dp, dataset_id, iterations, destroy_ratio, errors, ops_counter
):
    for _ in range(iterations):
        try:
            ds = dp.DatasetsProvider.get_dataset(dataset_id)
            if ds is None:
                raise RuntimeError("get_dataset returned None unexpectedly")

            if random.random() < destroy_ratio:
                with dp.datasets_lock:
                    should_destroy = dataset_id in dp.datasets
                if should_destroy:
                    dp.DatasetsProvider.destroy_dataset(dataset_id)

            with ops_counter["lock"]:
                ops_counter["count"] += 1
        except Exception:
            errors.append(traceback.format_exc())
            return


def _process_worker(
    worker_id,
    dataset_id,
    threads,
    iterations,
    destroy_ratio,
    start_event,
    result_queue,
    seed,
):
    random.seed(seed + worker_id)
    dp = _install_test_doubles()

    thread_errors = []
    ops_counter = {"count": 0, "lock": threading.Lock()}

    start_event.wait()

    thread_list = []
    for _ in range(threads):
        t = threading.Thread(
            target=_thread_worker,
            args=(
                dp,
                dataset_id,
                iterations,
                destroy_ratio,
                thread_errors,
                ops_counter,
            ),
        )
        t.start()
        thread_list.append(t)

    for t in thread_list:
        t.join()

    try:
        dp.DatasetsProvider.destroy_dataset(dataset_id)
    except Exception:
        thread_errors.append(traceback.format_exc())

    result_queue.put(
        {
            "worker_id": worker_id,
            "ops": ops_counter["count"],
            "errors": thread_errors,
        }
    )


def run_stress_test(
    workers,
    threads,
    iterations,
    destroy_ratio,
    dataset_id,
    start_timeout,
):
    ctx = get_context("spawn")
    start_event = ctx.Event()
    result_queue = ctx.Queue()

    processes = []
    for worker_id in range(workers):
        p = ctx.Process(
            target=_process_worker,
            args=(
                worker_id,
                dataset_id,
                threads,
                iterations,
                destroy_ratio,
                start_event,
                result_queue,
                12345,
            ),
        )
        p.start()
        processes.append(p)

    time.sleep(start_timeout)
    start_event.set()

    for p in processes:
        p.join()

    results = []
    for _ in processes:
        if not result_queue.empty():
            results.append(result_queue.get())

    total_ops = sum(result["ops"] for result in results)
    all_errors = []

    for result in results:
        if result["errors"]:
            for err in result["errors"]:
                all_errors.append((result["worker_id"], err))

    return total_ops, all_errors, results


def test_dataset_provider_stress_multiprocess_multithread():
    workers = 2
    threads = 4
    iterations = 50
    destroy_ratio = 0.30

    total_ops, all_errors, results = run_stress_test(
        workers=workers,
        threads=threads,
        iterations=iterations,
        destroy_ratio=destroy_ratio,
        dataset_id=FAKE_PROVIDER["id"],
        start_timeout=0.2,
    )

    expected_ops = workers * threads * iterations

    assert len(results) == workers
    assert not all_errors
    assert total_ops == expected_ops
