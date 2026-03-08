import requests
from datetime import datetime

def get_air_quality_data(latitude, longitude):
    """
    Fetches current air quality data for a given latitude and longitude
    using the Open-Meteo Air Quality API.
    """
    # Open-Meteo Air Quality API endpoint
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    
    # Parameters for the API request
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
        "timezone": "auto"
    }
    
    try:
        # print(f"Fetching air quality data for Lat: {latitude}, Lon: {longitude}...\n")
        response = requests.get(url, params=params)
        response.raise_for_status() # Check for HTTP errors
        
        data = response.json()
        current_data = data.get("current", {})
        
        if not current_data:
            print("No air quality data available for these coordinates.")
            return None
            
        # Extract the metrics
        time_str = current_data.get("time")
        aqi = current_data.get("us_aqi")
        pm25 = current_data.get("pm2_5")
        pm10 = current_data.get("pm10")
        co = current_data.get("carbon_monoxide")
        no2 = current_data.get("nitrogen_dioxide")
        ozone = current_data.get("ozone")
        
        # Format the time nicely
        date_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        formatted_time = date_obj.strftime("%b %d, %Y at %I:%M %p")
        
        # print(f"--- Current Air Quality as of {formatted_time} ---")
        # print("-" * 55)
        # print(f"US AQI:           {aqi} (Lower is better)")
        # print(f"PM2.5:            {pm25} μg/m³ (Fine particulate matter)")
        # print(f"PM10:             {pm10} μg/m³ (Coarse particulate matter)")
        # print(f"Ozone (O3):       {ozone} μg/m³")
        # print(f"Carbon Monoxide:  {co} μg/m³")
        # print(f"Nitrogen Dioxide: {no2} μg/m³")
        # print("-" * 55)
        
        return current_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# if __name__ == "__main__":
#     # Example coordinates: Los Angeles, CA, USA
#     test_lat = 38
#     test_lon = 77
    
#     # Example coordinates: New Delhi, India 
#     # test_lat = 28.6139
#     # test_lon = 77.2090
    
#     get_air_quality_data(test_lat, test_lon)