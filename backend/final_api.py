import concurrent.futures
import time
import json
from air_quality_api import get_air_quality_data
from census_api import get_us_demographics
from energy_api import get_energy_infrastructure
from env_risks_api import get_environmental_risk
from flood_api import get_flood_risk_data
from traffic_api import get_traffic_data
from tree_coverage_api import get_tree_coverage
from urban_heat_island_api import get_uhi_estimate     
from weather_api import get_weather_data
import os

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
        
        # Use ThreadPoolExecutor to run all requests at the exact same time
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            
            # Map our specific tasks and their arguments
            future_to_api = {
                executor.submit(get_air_quality_data, latitude, longitude): 'air_quality',
                executor.submit(get_us_demographics, latitude, longitude): 'census',
                executor.submit(get_energy_infrastructure, latitude, longitude): 'energy_infrastructure',
                executor.submit(get_environmental_risk, latitude, longitude): 'environmental_risks',
                executor.submit(get_flood_risk_data, latitude, longitude): 'flood_risk',
                executor.submit(get_traffic_data, latitude, longitude, self.tomtom_api_key): 'traffic',
                executor.submit(get_tree_coverage, latitude, longitude): 'tree_coverage',
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