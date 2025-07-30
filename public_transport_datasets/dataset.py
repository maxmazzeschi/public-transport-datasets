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

        print("process trips.txt")

        # Process the trips.txt file if we have extracted GTFS data
        if static_gtfs_url is not None and static_gtfs_url != "":
            try:
                import pandas as pd
                fname = os.path.join(temp_file_path, "trips.txt")
                
                # Check if the file exists before trying to process it
                if not os.path.exists(fname):
                    print(f"trips.txt not found in GTFS data for provider {self.src['id']}")
                    self.trip_last_stops = {}
                    return

                # Create a lookup dictionary for trip_id -> (trip_headsign, None)
                self.trip_last_stops = {}
                
                # Process file in chunks using pandas
                chunk_size = 10000
                total_processed = 0
                
                print(f"Processing trips.txt in chunks of {chunk_size}")
                
                # Read and process file in chunks
                for chunk_num, chunk in enumerate(pd.read_csv(
                    fname, 
                    chunksize=chunk_size,
                    usecols=['trip_id', 'trip_headsign'],
                    dtype={'trip_id': str, 'trip_headsign': str}
                )):
                    # Process this chunk: create lookup from trip_id to trip_headsign
                    for _, row in chunk.iterrows():
                        trip_id = row['trip_id']
                        trip_headsign = row['trip_headsign'] if pd.notna(row['trip_headsign']) else None
                        
                        # Store trip_headsign as the destination
                        self.trip_last_stops[trip_id] = (None, trip_headsign)
                    
                    total_processed += len(chunk)
                    
                    # Print progress every 10 chunks
                    if chunk_num % 10 == 0:
                        print(f"Processed chunk {chunk_num + 1}, total rows: {total_processed}")
                
                print(f"Created trip_last_stops lookup with {len(self.trip_last_stops)} entries from {total_processed} total trips")

            except Exception as e:
                print(
                    f"Error processing trips.txt: {e} provierId "
                    f"{self.src['id']}"
                )
                self.trip_last_stops = {}
        else:
            self.trip_last_stops = {}

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

        # Force garbage collection to free up memory
        import gc
        gc.collect()

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
        Get the destination information for a given trip_id from trips.txt.

        Args:
            trip_id (str): The trip ID to find the destination for.

        Returns:
           trip_headsign where trip_headsign is the destination,
            or None if not found.
        """
        if (
            hasattr(self, "trip_last_stops")
            and trip_id in self.trip_last_stops
        ):
            return self.trip_last_stops[trip_id]

        return None
