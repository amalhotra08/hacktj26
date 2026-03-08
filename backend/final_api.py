import concurrent.futures
import time
import json
from air_quality_api import get_air_quality_data
from census_api import get_us_demographics
from energy_api import get_energy_infrastructure
from env_risks_api import get_environmental_risk
from flood_api import get_flood_risk_data
from traffic_api import get_traffic_data
from urban_heat_island_api import get_uhi_estimate     
from weather_api import get_weather_data
import os
from dotenv import load_dotenv
from pathlib import Path
import math

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

try:
    from tree_coverage_api import get_tree_coverage as _get_tree_coverage
    _TREE_COVERAGE_IMPORT_ERROR = None
except Exception as exc:
    _get_tree_coverage = None
    _TREE_COVERAGE_IMPORT_ERROR = str(exc)


def safe_tree_coverage(min_lon, min_lat, max_lon, max_lat):
    if _get_tree_coverage is None:
        return {"error": f"tree coverage unavailable: {_TREE_COVERAGE_IMPORT_ERROR}"}
    try:
        return _get_tree_coverage(min_lon, min_lat, max_lon, max_lat)
    except Exception as exc:
        return {"error": f"tree coverage request failed: {exc}"}

def calculate_bounding_box(lat, lon, radius_km=1):
    """
    Takes a center latitude/longitude and draws a bounding box around it.
    Returns: min_lat, min_lon, max_lat, max_lon
    """
    # 1 degree of latitude is ~111 km
    lat_offset = radius_km / 111.0
    
    # 1 degree of longitude varies by latitude
    lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))
    
    min_lat = lat - lat_offset
    max_lat = lat + lat_offset
    min_lon = lon - lon_offset
    max_lon = lon + lon_offset
    
    return min_lat, min_lon, max_lat, max_lon

class LocationIntelligenceAnalyzer:
    def __init__(self, tomtom_api_key=None):
        """
        Initialize the analyzer. Pass any required API keys here so they 
        can be routed to the correct functions later.
        """
        self.tomtom_api_key = tomtom_api_key

    def generate_full_report(self, latitude, longitude):
        """
        Fires off all API calls concurrently and compiles the results into a single dictionary.
        """
        print(f"🌍 Generating comprehensive location report for Lat: {latitude}, Lon: {longitude}...")
        start_time = time.time()
        
        combined_report = {
            "metadata": {
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "data": {}
        }
        
# Calculate the bounding box for APIs that require an area instead of a point
        min_lat, min_lon, max_lat, max_lon = calculate_bounding_box(latitude, longitude, radius_km=1)

        # Use ThreadPoolExecutor to run all requests at the exact same time
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            
            future_to_api = {
                executor.submit(get_air_quality_data, latitude, longitude): 'air_quality',
                executor.submit(get_us_demographics, latitude, longitude): 'census',
                executor.submit(get_energy_infrastructure, latitude, longitude): 'energy_infrastructure',
                executor.submit(get_environmental_risk, latitude, longitude): 'environmental_risks',
                executor.submit(get_flood_risk_data, latitude, longitude): 'flood_risk',
                executor.submit(get_traffic_data, latitude, longitude, self.tomtom_api_key): 'traffic',
                
                executor.submit(safe_tree_coverage, min_lon, min_lat, max_lon, max_lat): 'tree_coverage',
                
                executor.submit(get_uhi_estimate, latitude, longitude): 'urban_heat_island',
                executor.submit(get_weather_data, latitude, longitude): 'weather'
            }
            
            # Collect the results as they finish (order doesn't matter here)
            for future in concurrent.futures.as_completed(future_to_api):
                api_name = future_to_api[future]
                try:
                    # Get the data returned by your individual functions
                    data = future.result()
                    combined_report["data"][api_name] = data
                except Exception as exc:
                    print(f"⚠️ {api_name} API generated an exception: {exc}")
                    combined_report["data"][api_name] = {"error": str(exc)}
                    
        end_time = time.time()
        print(f"\n✅ Full report generated in {end_time - start_time:.2f} seconds!")
        
        return combined_report

if __name__ == "__main__":
    TOMTOM_KEY = os.getenv("TOMTOM_KEY")
    
    # Initialize the master class
    analyzer = LocationIntelligenceAnalyzer(tomtom_api_key=TOMTOM_KEY)
    
    # Tysons, VA coordinates
    test_lat = 38.9187
    test_lon = -77.2311
    
    # Run the report
    master_report = analyzer.generate_full_report(test_lat, test_lon)
    
    # Print the final compiled data as nicely formatted JSON
    print("\n--- FINAL MASTER JSON OUTPUT ---")
    print(json.dumps(master_report, indent=4))
