import requests
import math

def calculate_rural_baseline_coords(lat, lon, distance_km=25):
    """
    Shifts the coordinates North-West by a specified distance to find a 
    (hopefully) more rural/suburban baseline outside the urban core.
    """
    # 1 degree of latitude is ~111 km
    lat_offset = distance_km / 111.0
    
    # 1 degree of longitude varies by latitude (cosine of lat)
    lon_offset = distance_km / (111.0 * math.cos(math.radians(lat)))
    
    # Shift North and West
    rural_lat = lat + lat_offset
    rural_lon = lon - lon_offset
    
    return round(rural_lat, 4), round(rural_lon, 4)

def get_uhi_estimate(urban_lat, urban_lon):
    """
    Estimates the real-time Urban Heat Island effect by comparing 
    temperatures at the target location vs a rural baseline.
    """
    rural_lat, rural_lon = calculate_rural_baseline_coords(urban_lat, urban_lon)
    
    # Open-Meteo endpoint
    url = "https://api.open-meteo.com/v1/forecast"
    
    # We pass both sets of coordinates in a single API call
    params = {
        "latitude": f"{urban_lat},{rural_lat}",
        "longitude": f"{urban_lon},{rural_lon}",
        "current": "temperature_2m,apparent_temperature",
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }
    
    try:
        # print(f"Fetching Urban vs Rural temperatures...")
        # print(f"Urban Core:    Lat {urban_lat}, Lon {urban_lon}")
        # print(f"Rural Offset:  Lat {rural_lat}, Lon {rural_lon} (~25km NW)\n")
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Open-Meteo returns a list of results when given multiple coordinates
        urban_data = data[0].get("current", {})
        rural_data = data[1].get("current", {})
        
        urban_temp = urban_data.get("temperature_2m")
        urban_feels = urban_data.get("apparent_temperature")
        
        rural_temp = rural_data.get("temperature_2m")
        rural_feels = rural_data.get("apparent_temperature")
        
        # Calculate the UHI Delta
        temp_delta = urban_temp - rural_temp
        feels_delta = urban_feels - rural_feels
        
        # print("--- Real-Time Urban Heat Island (UHI) Estimate ---")
        # print("-" * 50)
        # print(f"Target (Urban) Temp:    {urban_temp:.1f}°F (Feels like {urban_feels:.1f}°F)")
        # print(f"Baseline (Rural) Temp:  {rural_temp:.1f}°F (Feels like {rural_feels:.1f}°F)")
        # print("-" * 50)
        
        # if temp_delta > 0:
        #     print(f"🔥 UHI Effect Detected: The urban core is +{temp_delta:.1f}°F hotter.")
        #     if temp_delta > 3:
        #         print("   Status: Severe Heat Island Intensity.")
        #     elif temp_delta > 1:
        #         print("   Status: Moderate Heat Island Intensity.")
        # elif temp_delta < 0:
        #     print(f"🌳 Cool Island Effect: The target area is actually {abs(temp_delta):.1f}°F cooler.")
        #     print("   (This happens if the target is a large park, near water, or if the rural offset hit a mountain/desert).")
        # else:
        #     print("⚖️ No temperature difference detected right now.")
            
        # print("-" * 50)
        
        return {
            "urban_temp": urban_temp,
            "rural_temp": rural_temp,
            "uhi_delta": round(temp_delta, 2)
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching UHI data: {e}")
        return None

# if __name__ == "__main__":
#     # Example coordinates: Times Square, New York City (High UHI)
#     test_lat = 40.7580
#     test_lon = -73.9855
#     get_uhi_estimate(test_lat, test_lon)