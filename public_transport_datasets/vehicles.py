from abc import ABC, abstractmethod


class Vehicles(ABC):
    """Abstract base class for vehicles."""

    def __init__(self, url, headers, refresh_interval):
        """
        Initialize the Vehicles class.

        :param url: API endpoint URL
        :param headers: HTTP headers for API requests
        :param refresh_interval: Interval to refresh vehicle data
        """
        self.url = url
        self.headers = headers
        self.refresh_interval = refresh_interval

    @abstractmethod
    def get_vehicles_position(self, north, south, east, west, selected_routes):
        """Retrieve position for all vehicles in the bounding box"""
        pass

    @abstractmethod
    def get_routes_info(self):
        pass

    @abstractmethod
    def get_last_error(self):
        return None
