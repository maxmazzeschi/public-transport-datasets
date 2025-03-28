import requests
import os
import zipfile
import tempfile
from .gtfs_vehicles import GTFS_Vehicles
from .siri_vehicles import SIRI_Vehicles
from .tfl_vehicles import TFL_Vehicles
import uuid
import duckdb
import pandas as pd
from collections import defaultdict


class Dataset:
    def __init__(self, provider):
        self.src = provider
        self.vehicle_url = self.src["vehicle_positions_url"]
        if provider.get("authentication_type", 0) == 4:
            keyEnvVar = provider["vehicle_positions_url_api_key_env_var"]
            if keyEnvVar:
                print(f"getting {keyEnvVar}")
                api_key = os.getenv(keyEnvVar)
                if (api_key is None) or (api_key == ""):
                    trouble = f"API key not found in {keyEnvVar}"
                    print(trouble)
                    raise Exception(trouble)
                url = self.vehicle_url + api_key
            else:
                url = self.vehicle_url
        if provider["vehicle_positions_url_type"] == "SIRI":
            self.vehicles = SIRI_Vehicles(url, self.src["refresh_interval"])
        else:
            if provider["vehicle_positions_url_type"] == "TFL":
                self.vehicles = TFL_Vehicles("", self.src["refresh_interval"])
            else:
                self.vehicles = GTFS_Vehicles(
                    self.vehicle_url,
                    self.src.get("vehicle_positions_headers", None),
                    self.src["refresh_interval"],
                )
        static_gtfs_url = self.src["static_gtfs_url"]
        if static_gtfs_url:
            response = requests.get(self.src["static_gtfs_url"])
            temp_filename = tempfile.NamedTemporaryFile(
                suffix=".zip", delete=False
            ).name
            with open(temp_filename, "wb") as file:
                file.write(response.content)
            # Extract the ZIP file
            temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
            with zipfile.ZipFile(temp_filename, "r") as zip_ref:
                zip_ref.extractall(temp_file_path)
            os.remove(temp_filename)
            fname = os.path.join(temp_file_path, "stops.txt")
            # Connect to DuckDB (in-memory)
            con = duckdb.connect(database=":memory:")

            # Load the CSV file while handling missing values
            df = con.execute("""
                SELECT * FROM read_csv_auto('C:\\users\\maxma\downloads\\stops.txt', header=True, nullstr='')
            """).df()

            # Ensure stop_code is treated as a string and trim spaces
            df['stop_code'] = df['stop_code'].astype(str).str.strip()

            # Initialize dictionary to store multiple entries per stop_code
            self.stops_dict = defaultdict(list)

            # Populate the dictionary with all stop_code occurrences
            for _, row in df.iterrows():
                stop_code = row['stop_code']
                self.stops_dict[stop_code].append(row.to_dict())


            # os.removedirs(temp_file_path)
        else:
            self.stops_dict = {}

    def get_routes_info(self):
        return self.vehicles.get_routes_info()

    def get_vehicles_position(self, north, south, east, west, selected_routes):
        return self.vehicles.get_vehicles_position(
            north, south, east, west, selected_routes
        )

    def get_stops_info(self, north, south, east, west):
        result = []
        # Iterate over filtered data
        for stop_code, entries in self.stops_dict.items():
            for stop_data in entries:  # Iterate over the list of stops
                stop_lat = stop_data.get("stop_lat")
                stop_lon = stop_data.get("stop_lon")
                if isinstance(stop_lat, (int, float)) and south < stop_lat < north:
                    if isinstance(stop_lon, (int, float)) and west < stop_lon < east:
                        data = {"lat": stop_lat, "lon": stop_lon}
                        result.append(data)
        return result
