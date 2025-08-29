import time
import requests
from google.transit import gtfs_realtime_pb2
import threading
import logging
from .vehicles import Vehicles

# Configure logger for this module
logger = logging.getLogger(__name__)


class GTFS_Vehicles(Vehicles):
    def __init__(self, url, headers, refresh_interval, dataset=None):
        self.created_date = time.time()
        self.vehicle_list = []
        self.last_update = 0
        self.refresh_interval = refresh_interval
        self.vehicles_lock = threading.Lock()
        self.url = url
        self.headers = headers
        self.last_error = None
        self.dataset = dataset
        self._stop_requested = False  # Add stop flag
        self.last_request = time.time()
        self.update_vehicle_positions()
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()

    def update_vehicle_positions(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        try:
            if self.headers is not None:
                response = requests.get(self.url, headers=self.headers)
            else:
                response = requests.get(self.url)
            if response.status_code != 200:
                self.last_error = response
                logger.error(
                    f"Error {response.status_code} getting data from "
                    f"{self.url}"
                )
                return
            self.last_error = None
            feed.ParseFromString(response.content)
            last_update = int(feed.header.timestamp)
            if last_update == self.last_update:
                return
            self.last_update = feed.header.timestamp
        except Exception as e:
            self.last_error = e
            logger.error(f"Error fetching vehicle positions: {e} from "
                         f"{self.url}")
            return
        new_vehicles = []
        for entity in feed.entity:
            if entity.HasField("vehicle"):
                vehicle_id = entity.vehicle.vehicle.id
                route_id = entity.vehicle.trip.route_id
                if route_id == "":
                    route_id = entity.vehicle.vehicle.label
                latitude = entity.vehicle.position.latitude
                longitude = entity.vehicle.position.longitude
                bearing = entity.vehicle.position.bearing
                speed = entity.vehicle.position.speed
                new_vehicles.append(
                    {
                        "vehicle_id": vehicle_id,
                        "route_id": route_id,
                        "trip_id": entity.vehicle.trip.trip_id,
                        "lat": latitude,
                        "lon": longitude,
                        "bearing": bearing,
                        "speed": speed,
                    }
                )
        with self.vehicles_lock:
            self.vehicle_list = new_vehicles

    def stop(self):
        """Stop the update thread gracefully"""
        self._stop_requested = True

    def update_loop(self):
        while not self._stop_requested:  # Check stop flag
            if (time.time() - self.last_request) > 10*60:
                logger.error(
                    f"Last request was more than 10 minutes ago. Stopping update thread."
                )
                from .datasets_provider import DatasetsProvider
                DatasetsProvider.destroy_dataset(self.dataset.src['id'])
                
                return
            self.update_vehicle_positions()
            time.sleep(self.refresh_interval)

    def get_vehicles_position(self, north, south, east, west, selected_routes):
        """
        Fetches vehicle positions within the specified bounding box and for
          selected routes.

        Args:
            north (float): Northern latitude boundary.
            south (float): Southern latitude boundary.
            east (float): Eastern longitude boundary.
            west (float): Western longitude boundary.
            selected_routes (str): Comma-separated route IDs to
            filter vehicles.

        Returns:
            dict: A dictionary containing created_date, last_update, and
            filtered vehicles.
        """
        self.last_request = time.time()
        north = float(north)
        south = float(south)
        east = float(east)
        west = float(west)
        selected_routes = selected_routes.split(",") if selected_routes else []
        with self.vehicles_lock:
            filtered_vehicles = []
            for v in self.vehicle_list:
                if (
                    south <= v["lat"] <= north
                    and west <= v["lon"] <= east
                    and (
                        not selected_routes or v["route_id"] in selected_routes
                    )
                ):
                    # Create a copy of the vehicle data
                    vehicle_data = v.copy()

                    # Get last stop information if dataset is available
                    # and trip_id exists
                    if self.dataset and "trip_id" in v:
                        result = self.dataset.get_last_stop(v["trip_id"])
                        if result is not None:
                            stop_id, stop_name = result
                        else:
                            stop_id, stop_name = None, None
                        vehicle_data["last_stop_id"] = stop_id
                        vehicle_data["last_stop_name"] = stop_name
                    else:
                        vehicle_data["last_stop_id"] = None
                        vehicle_data["last_stop_name"] = None

                    # Log vehicle data for debugging if needed
                    logger.debug(f"Vehicle data: {vehicle_data}")
                    filtered_vehicles.append(vehicle_data)
        return {
            "created_date": self.created_date,
            "last_update": self.last_update,
            "vehicles": filtered_vehicles,
            "last_error": self.last_error,
        }

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

    def cleanup(self, ds):
        try:
            # Clean up dataset resources outside the lock
            if hasattr(ds, 'vehicles'):
                if hasattr(ds.vehicles, 'stop'):
                    ds.vehicles.stop()  # Gracefully stop the update thread
                if hasattr(ds.vehicles, 'update_thread') and ds.vehicles.update_thread.is_alive():
                    ds.vehicles.update_thread.join(timeout=5)  # Wait up to 5 seconds for thread to stop
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
