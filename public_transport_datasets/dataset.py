import requests
import os
import zipfile
import tempfile
from .gtfs_vehicles import GTFS_Vehicles
from .siri_vehicles import SIRI_Vehicles
from .tfl_vehicles import TFL_Vehicles
import uuid
import duckdb
import geopandas as gpd
from shapely.geometry import Point, box
import shutil
import csv


class Dataset:
    def __init__(self, provider):
        print(
            f"init dataset {provider['id']} "
            f"{provider['country']} {provider['city']}"
        )
        self.src = provider
        self.vehicle_url = self.src["vehicle_positions_url"]

        static_gtfs_url = self.src.get("static_gtfs_url")
        if static_gtfs_url is not None and static_gtfs_url != "":
            temp_filename = tempfile.NamedTemporaryFile(
                suffix=".zip", delete=False
            ).name
            temp_file_path = os.path.join(
                tempfile.gettempdir(), f"{uuid.uuid4()}"
            )
            try:
                os.makedirs(temp_file_path, exist_ok=True)
                response = requests.get(self.src["static_gtfs_url"])
                if response.status_code != 200:
                    raise Exception(
                        f"Error {response.status_code} {response.headers}"
                        f" getting data from {self.src['static_gtfs_url']}"
                    )

                with open(temp_filename, "wb") as file:
                    file.write(response.content)
                # Extract the ZIP file

                with zipfile.ZipFile(temp_filename, "r") as zip_ref:
                    zip_ref.extractall(temp_file_path)
                os.remove(temp_filename)
            except Exception as e:
                print(
                    f"Error downloading GTFS data: {e} {temp_filename}"
                    f" provierId {self.src['id']}"
                )
                self.gdf = None
                return
            # Process the stops.txt file
            try:
                fname = os.path.join(temp_file_path, "stops.txt")

                # Connect to DuckDB (in-memory)
                con = duckdb.connect(database=":memory:")

                # Check if stop_code exists in the CSV file
                with open(fname, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader)  # Read the first line as headers

                # Dynamically set types based on the presence of stop_code
                types = {"stop_id": "VARCHAR"}
                if "stop_code" in headers:
                    types["stop_code"] = "VARCHAR"

                # Load the CSV file while handling missing values
                df = con.execute(
                    f"""
                    SELECT
                        *
                    FROM read_csv_auto(
                        '{fname}',
                        header=True,
                        nullstr='',
                        types={types}
                    )
                    """
                ).df()

                # Ensure stop_code or stop_id is treated as a
                # string and trim spaces
                if "stop_code" in df.columns:
                    df["stop_code"] = df["stop_code"].astype(str).str.strip()
                else:
                    df["stop_code"] = df["stop_id"].astype(str).str.strip()

                df["stop_name"] = df["stop_name"].astype(str).str.strip()

                # Create a GeoDataFrame with geometry column
                # Assuming 'stop_lat' and 'stop_lon' columns exist in the data
                df["geometry"] = df.apply(
                    lambda row: Point(row["stop_lon"], row["stop_lat"]), axis=1
                )
                self.gdf = gpd.GeoDataFrame(df, geometry="geometry")

                # Set the coordinate reference system (CRS)
                # to WGS84 (EPSG:4326)
                self.gdf.set_crs(epsg=4326, inplace=True)

            except Exception as e:
                print(
                    f"Error processing GTFS data: {e} {fname} provierId "
                    f"{self.src['id']}"
                )
                raise e
        else:
            self.gdf = None
            self.stop_times = None
        print("process stop_times.txt")

        # Process the stop_times.txt file if we have extracted GTFS data
        if static_gtfs_url is not None and static_gtfs_url != "":
            try:
                fname = os.path.join(temp_file_path, "stop_times.txt")

                # Connect to DuckDB (in-memory)
                con = duckdb.connect(database=":memory:")

                # Check if stop_code exists in the CSV file
                with open(fname, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader)  # Read the first line as headers
                    types = {"stop_id": "VARCHAR", "trip_id": "VARCHAR"}
                    if "stop_code" in headers:
                        types["stop_code"] = "VARCHAR"

                    # Load the CSV file while handling missing values
                    stop_times = con.execute(
                        f"""
                        SELECT
                            *
                        FROM read_csv_auto(
                            '{fname}',
                            header=True,
                            nullstr='',
                            types={types}
                        )
                        """
                    ).df()

                # Ensure stop_code or stop_id is treated as a string and
                # trim spaces
                if "stop_code" in stop_times.columns:
                    stop_times["stop_code"] = (
                        stop_times["stop_code"].astype(str).str.strip()
                    )

                # Store stop_times as instance variable
                self.stop_times = stop_times

                # Create a lookup dictionary for trip_id ->
                #   (latest_stop_id, stop_name)
                self.trip_last_stops = {}
                if self.gdf is not None:
                    try:
                        # Group by trip_id and find the maximum stop_sequence
                        #  for each trip
                        last_stops = stop_times.loc[
                            stop_times.groupby("trip_id")[
                                "stop_sequence"
                            ].idxmax()
                        ]

                        # Create a dictionary mapping trip_id to stop_id
                        trip_to_stop = dict(
                            zip(last_stops["trip_id"], last_stops["stop_id"])
                        )

                        # Create a dictionary mapping stop_id to stop_name
                        # from gdf
                        stop_to_name = dict(
                            zip(self.gdf["stop_id"], self.gdf["stop_name"])
                        )

                        # Combine to create final lookup
                        for trip_id, stop_id in trip_to_stop.items():
                            stop_name = stop_to_name.get(stop_id, None)
                            self.trip_last_stops[trip_id] = (
                                stop_id,
                                stop_name,
                            )

                        print(
                            f"Created trip_last_stops lookup with "
                            f"{len(self.trip_last_stops)} entries"
                        )
                    except Exception as e:
                        print(f"Error creating trip_last_stops lookup: {e}")
                        self.trip_last_stops = {}
                else:
                    self.trip_last_stops = {}

            except Exception as e:
                print(
                    f"Error processing stop_times.txt: {e} provierId "
                    f"{self.src['id']}"
                )
                self.stop_times = None
        # After processing the files, remove the temp_file_path folder
        # print(f"temporary files at {temp_file_path}")
        shutil.rmtree(temp_file_path, ignore_errors=True)
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
                    self,
                )

    def get_routes_info(self):
        return self.vehicles.get_routes_info()

    def get_vehicles_position(self, north, south, east, west, selected_routes):
        return self.vehicles.get_vehicles_position(
            north, south, east, west, selected_routes
        )

    def get_stops_in_area(self, north, south, east, west):
        """
        Get stops within a bounding box area.

        Args:
            north (float): Northern latitude boundary.
            south (float): Southern latitude boundary.
            east (float): Eastern longitude boundary.
            west (float): Western longitude boundary.

        Returns:
            list: List of dictionaries containing stop information.
        """
        if self.gdf is None:
            return []

        # Create a bounding box
        bounding_box = box(west, south, east, north)

        # Filter stops within the bounding box
        filtered_stops = self.gdf[self.gdf.geometry.within(bounding_box)]

        # Create list of dictionaries
        stops_list = [
            {
                "lat": point.y,
                "lon": point.x,
                "stop_name": stop_name,
                "stop_id": stop_id,
                "stop_code": stop_code,
            }
            for point, stop_name, stop_code, stop_id in zip(
                filtered_stops.geometry,
                filtered_stops["stop_name"],
                filtered_stops["stop_id"],
                filtered_stops["stop_code"],
            )
        ]

        return stops_list

    def get_last_stop(self, trip_id):
        """
        Get the last stop for a given trip_id.

        Args:
            trip_id (str): The trip ID to find the last stop for.

        Returns:
            tuple: (stop_id, stop_name) of the last stop, or (None, None)
            if not found.
        """
        if (
            hasattr(self, "trip_last_stops")
            and trip_id in self.trip_last_stops
        ):
            return self.trip_last_stops[trip_id]

        # Fallback to original method if lookup not available
        if self.stop_times is None or self.gdf is None:
            return None, None

        try:
            # Filter stop_times for the given trip_id
            trip_stops = self.stop_times[self.stop_times["trip_id"] == trip_id]

            if trip_stops.empty:
                return None, None

            # Get the row with the maximum stop_sequence
            last_row = trip_stops.loc[trip_stops["stop_sequence"].idxmax()]
            stop_id = last_row["stop_id"]

            # Get stop_name from the geodataframe (stops data)
            stop_info = self.gdf[self.gdf["stop_id"] == stop_id]

            if stop_info.empty:
                return stop_id, None

            stop_name = stop_info["stop_name"].values[0]
            return stop_id, stop_name

        except Exception as e:
            print(f"Error getting last stop for trip {trip_id}: {e}")
            return None, None
