import requests

def get_energy_infrastructure(latitude, longitude, radius_meters=5000):
    """
    Fetches nearby energy infrastructure (substations, plants, lines) 
    within a specific radius using the OpenStreetMap Overpass API.
    """
    # Overpass API endpoint
    url = "http://overpass-api.de/api/interpreter"
    
    # Overpass QL (Query Language) to find "power" tags within the radius
    # [out:json] tells it to return JSON data
    # (around:radius,lat,lon) sets the search area
    query = f"""
    [out:json];
    (
      node["power"](around:{radius_meters},{latitude},{longitude});
      way["power"](around:{radius_meters},{latitude},{longitude});
      relation["power"](around:{radius_meters},{latitude},{longitude});
    );
    out tags;
    """
    
    try:
        print(f"Scanning for energy infrastructure within {radius_meters}m of Lat: {latitude}, Lon: {longitude}...\n")
        response = requests.post(url, data={'data': query})
        response.raise_for_status()
        
        data = response.json()
        elements = data.get("elements", [])
        
        if not elements:
            print("No major energy infrastructure found in this radius.")
            return None
            
        # Dictionary to tally up what we find
        infrastructure_counts = {}
        
        for el in elements:
            tags = el.get("tags", {})
            power_type = tags.get("power", "unknown")
            
            # Tally the types of infrastructure (e.g., 'tower', 'substation', 'line')
            if power_type in infrastructure_counts:
                infrastructure_counts[power_type] += 1
            else:
                infrastructure_counts[power_type] = 1
                
        print("--- Local Energy Infrastructure Found ---")
        print("-" * 39)
        
        # Print the tallied results cleanly
        for infra_type, count in sorted(infrastructure_counts.items()):
            # Capitalize and format nicely
            formatted_type = infra_type.replace('_', ' ').title()
            print(f"{formatted_type:<20}: {count}")
            
        print("-" * 39)
        print(f"Total features mapped: {len(elements)}")
        
        return infrastructure_counts

    except requests.exceptions.RequestException as e:
        print(f"Error fetching infrastructure data: {e}")
        return None


# if __name__ == "__main__":
#     # Example coordinates: Near a major power plant or substation
#     # Let's use the Tysons, VA area coordinates from earlier
#     test_lat = 38.9187
#     test_lon = -77.2311
    
#     get_energy_infrastructure(test_lat, test_lon, radius_meters=5000)