import time
import requests
import threading
from jsonpath_ng import parse
from .vehicles import Vehicles


class SIRI_Vehicles(Vehicles):
    def __init__(self, url, refresh_interval):
        print(url)
        self.created_date = time.time()
        self.vehicle_list = []
        self.last_update = 0
        self.refresh_interval = refresh_interval
        self.vehicles_lock = threading.Lock()
        self.url = url
        self.last_error = None
        self.update_vehicle_positions()
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()

    def update_vehicle_positions(self):
        print("update_vehicle_positions")
        try:
            response = requests.get(self.url)
            print("Response: ", response)
            data = response.json()
            self.last_update = time.time()
            # JSONPath Query: Select all VehicleActivity objects
            expr = parse(
                "$.Siri.ServiceDelivery.VehicleMonitoringDelivery[0].VehicleActivity[*]"
            )
            matches = [match.value for match in expr.find(data)]
            new_vehicles = []
            for match in matches:
                vehicle_id = match["MonitoredVehicleJourney"]["VehicleRef"]
                route_id = match["MonitoredVehicleJourney"]["PublishedLineName"]
                latitude = match["MonitoredVehicleJourney"]["VehicleLocation"]["Latitude"]
                longitude = match["MonitoredVehicleJourney"]["VehicleLocation"]["Longitude"]
                bearing = match["MonitoredVehicleJourney"]["Bearing"]
                speed = "0"
                new_vehicles.append(
                    {
                        "vehicle_id": vehicle_id,
                        "route_id": route_id,
                        "lat": latitude,
                        "lon": longitude,
                        "bearing": bearing,
                        "speed": speed,
                    }
                )
            with self.vehicles_lock:
                self.vehicle_list = new_vehicles
            # print(f"Updated vehicle positions: {len(self.vehicles)}")
        except Exception as e:
            self.last_error = e
            print(f"Error fetching vehicle positions aaa: {e}")

    def update_loop(self):
        while True:
            self.update_vehicle_positions()
            time.sleep(self.refresh_interval)

    def get_vehicles_position(self, north, south, east, west, selected_routes):
        north = float(north)
        south = float(south)
        east = float(east)
        west = float(west)
        selected_routes = selected_routes.split(",") if selected_routes else []
        with self.vehicles_lock:
            filtered_vehicles = [
                v
                for v in self.vehicle_list
                if south <= v["lat"] <= north
                and west <= v["lon"] <= east
                and (not selected_routes or v["route_id"] in selected_routes)
            ]
        return {
            "created_date": self.created_date,
            "last_update": self.last_update,
            "vehicles": filtered_vehicles,
        }

    def get_available_routes(self):
        with self.vehicles_lock:
            route_ids = list({v["route_id"] for v in self.vehicle_list})
        return route_ids

    def get_last_error(self):
        return self.last_error

    def get_routes_info(self):
        route_ids = []
        min_lat = float("inf")
        max_lat = float("-inf")
        min_lon = float("inf")
        max_lon = float("-inf")

        # Loop through all vehicle data entries
        for data in self.vehicle_list:
            route_ids.append(data["route_id"])
            if data["lat"] == 0:
                continue
            if data["lon"] == 0:
                continue
            min_lat = min(min_lat, data["lat"])
            max_lat = max(max_lat, data["lat"])
            min_lon = min(min_lon, data["lon"])
            max_lon = max(max_lon, data["lon"])

        return {
            "route_ids": list(set(route_ids)),  # Unique route_id list
            "min_latitude": min_lat,
            "max_latitude": max_lat,
            "min_longitude": min_lon,
            "max_longitude": max_lon,
        }
