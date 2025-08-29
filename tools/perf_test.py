import sys
import os
import time  # Add this import

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from public_transport_datasets.datasets_provider import DatasetsProvider

# Measure execution time of line 14

ds = DatasetsProvider.get_dataset(
    "ed4eec6d021b7820b75e174ba1f00801eb9900408f7be54a209e3d5bfcd24eeb"
)

start_time = time.time()
v = ds.get_vehicles_position(90, -90, +180, -180, "")
print(v)
end_time = time.time()
execution_time = end_time - start_time
print(f"execution time: {execution_time:.4f} seconds")

start_time = time.time()
ds.get_vehicles_position(90, -90, +180, -180, "")
end_time = time.time()
execution_time = end_time - start_time
print(f"execution time: {execution_time:.4f} seconds")


start_time = time.time()
ds.get_vehicles_position(90, -90, +180, -180, "")
end_time = time.time()
execution_time = end_time - start_time
print(f"execution time: {execution_time:.4f} seconds")

exit()