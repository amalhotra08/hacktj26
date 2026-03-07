import requests

def get_traffic_data(latitude, longitude, api_key):
    """
    Fetches live traffic flow data for a given latitude and longitude
    using the TomTom Traffic API.
    """
    # TomTom Traffic Flow API endpoint
    # 'absolute' style returns actual speeds, '10' is a standard zoom level
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    
    params = {
        "key": api_key,
        "point": f"{latitude},{longitude}",
        "unit": "mph" # Can be changed to 'KMPH'
    }
    
    try:
        print(f"Fetching traffic data for Lat: {latitude}, Lon: {longitude}...\n")
        response = requests.get(url, params=params)
        
        # If the API key is invalid or missing, catch it early
        if response.status_code in [401, 403]:
            print("Error: Invalid or missing TomTom API Key.")
            return None
            
        response.raise_for_status() 
        data = response.json()
        
        # Extract the flow data
        flow_data = data.get("flowSegmentData", {})
        
        if not flow_data:
            print("No traffic data available for this specific road segment.")
            return None
            
        current_speed = flow_data.get("currentSpeed")
        free_flow_speed = flow_data.get("freeFlowSpeed")
        
        # Calculate a basic congestion metric
        if free_flow_speed and free_flow_speed > 0:
            speed_ratio = current_speed / free_flow_speed
            
            if speed_ratio >= 0.90:
                status = "🟢 Clear (Normal speeds)"
            elif speed_ratio >= 0.65:
                status = "🟡 Moderate Congestion (Slowed down)"
            else:
                status = "🔴 Heavy Traffic (Significant delays)"
        else:
            status = "⚪ Unknown"

        print("--- Live Traffic Flow ---")
        print("-" * 35)
        print(f"Current Speed:    {current_speed} mph")
        print(f"Free Flow Speed:  {free_flow_speed} mph (Normal speed limit without traffic)")
        print(f"Status:           {status}")
        print("-" * 35)
        
        return flow_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching traffic data: {e}")
        return None

# --- Example Usage ---
# --- Example Usage ---
if __name__ == "__main__":
    # Remember to use a newly generated API key!
    TOMTOM_API_KEY = "f49bSLLOsW9c8bwQ5PZSq0QHdh0czJR1" 
    
    # Precise coordinates near Tysons, VA (Intersection of Rt 7 & Rt 123)
    test_lat = 38.9187
    test_lon = -77.2311
    
    get_traffic_data(test_lat, test_lon, TOMTOM_API_KEY)