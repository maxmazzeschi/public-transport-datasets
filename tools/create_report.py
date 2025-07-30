import sys
import os
import time  # Add this import


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from public_transport_datasets.datasets_provider import DatasetsProvider

# Measure execution time of line 14

ds = DatasetsProvider.get_dataset(
    "bffc9fddc1a42ea392e30a232eb7206130569b2414c91bbc90208f38027127df"
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

dss = DatasetsProvider.get_all_datasets()
active_datasets = {}
not_active_datasets = {}
for dataset in dss.values():
    if dataset["enabled"] is True:
        country = dataset["country"]
        if country not in active_datasets:
            active_datasets[country] = []
        active_datasets[country].append(dataset)
    else:
        country = dataset["country"]
        if country not in not_active_datasets:
            not_active_datasets[country] = []
        not_active_datasets[country].append(dataset)
with open("../Report.md", "w", encoding="utf-8") as f:
    f.write("# Public Transport Datasets Report\n")
    f.write("## Active Datasets\n")
    f.write(
        "| Country | City | Vechicles | Speed Info "
        "| Bearing Info | Has stops |"
        " ENV VAR for API KEY|Issued by|\n"
    )
    f.write(
        "| ------- | ---- | --------- | ---------- | ------------ | "
        "--------- | ----------------- | ------- |\n"
    )
    for country, datasets in active_datasets.items():
        for dataset in datasets:
            city = dataset["city"]
            ds_id = dataset["id"]
            ds = DatasetsProvider.get_dataset(ds_id)
            schedule_url = dataset.get("static_gtfs_url", None)
            stops = "?"
            if schedule_url is None:
                stops = "No"
            elif schedule_url == "":
                stops = "?"
            else:
                stops = "Yes"
            vehicle_list = ds.get_vehicles_position(90, -90, +180, -180, "")
            if vehicle_list["last_error"] is not None:
                info = vehicle_list["last_error"]
                speed_info = 0
                bearing_info = 0
            else:
                info = len(vehicle_list["vehicles"])
                if info > 0:
                    speeds = [
                        vehicle["speed"]
                        for vehicle in vehicle_list["vehicles"]
                        if vehicle.get("speed", 0) > 0
                    ]
                    speed_info = len(speeds) / info * 100
                    bearings = [
                        vehicle["bearing"]
                        for vehicle in vehicle_list["vehicles"]
                        if vehicle.get("bearing", 0) > 0
                    ]
                    if len(bearings) > 0:
                        bearing_info = len(bearings) / info * 100
                    else:
                        bearing_info = 0
                else:
                    speed_info = 0
                    bearing_info = 0
            limit = 40
            if city is not None:
                if len(city) > limit:
                    city = city[: limit - 3] + "..."
            api_env_var = dataset.get(
                "vehicle_positions_url_api_key_env_var", ""
            )
            issued_by = dataset.get("authentication_info_url", "")
            if api_env_var is None:
                api_env_var = ""
            f.write(
                (
                    f"|{country}|{city}|{info}|{speed_info:.2f}%|"
                    f"{bearing_info:.2f}%|{stops}|{api_env_var}|{issued_by}|\n"
                )
            )
    f.write("\n")
    f.write("\n")
    f.write("## Work in Progress Datasets\n")
    f.write("| Country | City | Authentication |\n")
    f.write("| ------- | ---- | ----------- |\n")

    for country, datasets in not_active_datasets.items():
        for dataset in datasets:
            city = dataset["city"]
            limit = 40
            if city is not None:
                if len(city) > limit:
                    city = city[: limit - 3] + "..."
            f.write(f"|{country}|{city}|{dataset['authentication_type']}|\n")
