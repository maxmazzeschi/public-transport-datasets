import requests
import os
import zipfile
import tempfile
from .gtfs_vehicles import GTFS_Vehicles
from .siri_vehicles import SIRI_Vehicles
from .tfl_vehicles import TFL_Vehicles
import uuid


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
            # os.removedirs(temp_file_path)

    def get_routes_info(self):
        return self.vehicles.get_routes_info()

    def get_vehicles_position(self, north, south, east, west, selected_routes):
        return self.vehicles.get_vehicles_position(
            north, south, east, west, selected_routes
        )
