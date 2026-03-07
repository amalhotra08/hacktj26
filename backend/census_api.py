import requests

def get_land_use_data(latitude, longitude, radius_meters=1000):
    """
    Scans a radius around the coordinates to tally the types of land use 
    (residential, commercial, retail, etc.) using the Overpass API.
    """
    url = "http://overpass-api.de/api/interpreter"
    
    # Query OSM for anything tagged with "landuse" in the radius
    query = f"""
    [out:json];
    (
      way["landuse"](around:{radius_meters},{latitude},{longitude});
      relation["landuse"](around:{radius_meters},{latitude},{longitude});
    );
    out tags;
    """
    
    try:
        print(f"Scanning land use within {radius_meters}m of Lat: {latitude}, Lon: {longitude}...\n")
        response = requests.post(url, data={'data': query})
        response.raise_for_status()
        
        elements = response.json().get("elements", [])
        
        if not elements:
            print("No specific land use zoning data found for this area.")
            return None
            
        land_use_counts = {}
        
        for el in elements:
            tags = el.get("tags", {})
            use_type = tags.get("landuse", "unknown")
            
            if use_type in land_use_counts:
                land_use_counts[use_type] += 1
            else:
                land_use_counts[use_type] = 1
                
        print("--- Local Land Use Zoning (OSM) ---")
        print("-" * 35)
        
        for use_type, count in sorted(land_use_counts.items(), key=lambda x: x[1], reverse=True):
            formatted_type = use_type.replace('_', ' ').title()
            print(f"{formatted_type:<15}: {count} parcels/zones")
            
        print("-" * 35)
        return land_use_counts

    except requests.exceptions.RequestException as e:
        print(f"Error fetching land use data: {e}")
        return None

def get_us_demographics(latitude, longitude):
    """
    Converts coordinates to a US Census Tract and fetches local population 
    and median income data from the American Community Survey (ACS).
    """
    try:
        print("\nFetching US Census Demographic Data...")
        
        # Step 1: Get the Census FIPS code using the FCC Geocoder API
        fcc_url = f"https://geo.fcc.gov/api/census/block/find?latitude={latitude}&longitude={longitude}&format=json"
        fcc_response = requests.get(fcc_url)
        fcc_response.raise_for_status()
        
        fips = fcc_response.json().get('Block', {}).get('FIPS', '')
        
        if not fips:
            print("Could not find US Census data for these coordinates. (Are you outside the US?)")
            return None
            
        # Parse the FIPS code into State, County, and Tract
        state = fips[0:2]
        county = fips[2:5]
        tract = fips[5:11]
        
        # Step 2: Query the US Census API (2022 ACS 5-Year Estimates)
        # B01003_001E = Total Population, B19013_001E = Median Household Income
        census_url = "https://api.census.gov/data/2022/acs/acs5"
        params = {
            "get": "NAME,B01003_001E,B19013_001E",
            "for": f"tract:{tract}",
            "in": f"state:{state} county:{county}"
        }
        
        census_response = requests.get(census_url, params=params)
        census_response.raise_for_status()
        
        data = census_response.json()
        
        # Data comes back as a list of lists: [Headers], [Values]
        if len(data) > 1:
            name = data[1][0]
            population = data[1][1]
            income = data[1][2]
            
            # Format income cleanly
            formatted_income = f"${int(income):,}" if income is not None and int(income) > 0 else "Data Unavailable"
            formatted_pop = f"{int(population):,}" if population is not None else "Unknown"
            
            print("--- Neighborhood Demographics ---")
            print("-" * 40)
            print(f"Area:           {name}")
            print(f"Population:     {formatted_pop} people")
            print(f"Median Income:  {formatted_income}")
            print("-" * 40)
            
            return {"population": population, "median_income": income}
        else:
            print("No demographic data found for this specific tract.")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching demographic data: {e}")
        return None

# if __name__ == "__main__":
#     # Tysons, VA (Intersection of Rt 7 & Rt 123)
#     test_lat = 38.9187
#     test_lon = -77.2311
    
#     get_land_use_data(test_lat, test_lon, radius_meters=1000)
#     get_us_demographics(test_lat, test_lon)