import requests
from datetime import datetime

def get_flood_risk_data(latitude, longitude):
    """
    Fetches daily river discharge data for a given latitude and longitude
    using the Open-Meteo Global Flood API.
    """
    # Open-Meteo Flood API endpoint
    url = "https://flood-api.open-meteo.com/v1/flood"
    
    # Parameters for the API request
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "river_discharge",
        "timezone": "auto",
        "forecast_days": 3 # Pulls today and the next 2 days of forecast
    }
    
    try:
        print(f"Fetching flood risk data for Lat: {latitude}, Lon: {longitude}...\n")
        response = requests.get(url, params=params)
        response.raise_for_status() # Check for HTTP errors
        
        data = response.json()
        
        # Extract the daily data
        daily_data = data.get("daily", {})
        dates = daily_data.get("time", [])
        discharges = daily_data.get("river_discharge", [])
        
        if not dates or not discharges:
            print("No water system data available for these coordinates.")
            return None
            
        print("--- River Discharge Forecast ---")
        print("Unit: Cubic meters per second (m³/s)")
        print("-" * 32)
        
        # Loop through and print the paired dates and values
        results = []
        for date_str, discharge in zip(dates, discharges):
            # Format the date nicely
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%b %d, %Y")
            
            # Handle potential null values if coordinates are far from a river
            if discharge is None:
                discharge_val = "0.00 (or no river nearby)"
            else:
                discharge_val = f"{discharge:.2f}"
                
            print(f"{formatted_date}: {discharge_val} m³/s")
            
            results.append({"date": date_str, "discharge_m3_s": discharge})
            
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # Example coordinates: New Orleans, LA, USA (High flood risk area)
    test_lat = 38
    test_lon = 77
    
    # Example coordinates: Paris, France (Seine River)
    # test_lat = 48.8566
    # test_lon = 2.3522
    
    get_flood_risk_data(test_lat, test_lon)