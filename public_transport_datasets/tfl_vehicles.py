import time
import threading
from .rate_limited_session import RateLimitedSession
from .vehicles import Vehicles


class TFL_Vehicles(Vehicles):
    def __init__(self, url, refresh_interval):
        print(url)
        self.session = RateLimitedSession(max_requests_per_minute=50)
        self.created_date = time.time()
        self.vehicle_list = []
        self.last_update = 0
        self.refresh_interval = refresh_interval
        self.vehicles_lock = threading.Lock()
        self.url = url
        self.update_vehicle_positions()
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()

    def get_active_bus_routes(self):
        url = "https://api.tfl.gov.uk/Line/Mode/bus"
        response = self.session.get(url)
        if response.status_code == 200:
            return [line["id"] for line in response.json()]
        return []

    def tfl_data(self, route):
        url = f"https://api.tfl.gov.uk/Line/{route}/Arrivals"
        response = self.session.get(url)
        if response.status_code == 200:
            positions = []
            vehicles = response.json()
            for v in vehicles:
                positions.append(
                    {
                        "vehicle_id": v.get("vehicleId"),
                        "latitude": v.get("latitude"),
                        "longitude": v.get("longitude"),
                        "timestamp": v.get("timestamp"),
                        "route_id": route,
                        "bearing": v.get("bearing"),
                        "speed": v.get("speed", 0),
                    }
                )
            return positions
        print(f"error {response.status_code}")
        print(self.session.dump())
        return []

    def update_vehicle_positions(self):
        new_vehicles = []
        routes = self.get_active_bus_routes()
        print(f"Found {len(routes)} active bus routes.")
        for index, route in enumerate(routes, start=1):
            print(f"Processing route {index} of {len(routes)}: {route}")
            vehicles = self.tfl_data(route)
            new_vehicles.extend(vehicles)
            time.sleep(0.2)  # To prevent rate limiting
        with self.vehicles_lock:
            self.vehicle_list = new_vehicles
            print(f"Updated vehicle positions: {len(self.vehicle_list)}")
            print(self.vehicle_list[0])

    def update_loop(self):
        while True:
            self.update_vehicle_positions()
            time.sleep(self.refresh_interval)

    def get_vehicles_positions(
        self, north, south, east, west, selected_routes
    ):
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
