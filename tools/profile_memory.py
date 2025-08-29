import tracemalloc
import argparse
import runpy
import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from public_transport_datasets.datasets_provider import DatasetsProvider

def main():
    parser = argparse.ArgumentParser(description="Profile memory usage of a Python app.")
    parser.add_argument("script", help="The Python script you want to profile")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the target script")
    args = parser.parse_args()

    # Start tracking memory allocations
    tracemalloc.start()

    print("Run target script in same process")
    runpy.run_path(args.script, run_name="__main__")

    print("Take snapshot after script finishes")
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("lineno")

    print("\nTop 10 memory-consuming lines:")
    for stat in top_stats[:10]:
        print(stat)

    # Show total memory allocated
    total = sum(stat.size for stat in top_stats)
    print(f"\nTotal allocated memory: {total / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
