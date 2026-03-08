import requests

def get_environmental_risk(latitude, longitude):
    """
    Fetches the FEMA National Risk Index (NRI) ratings for natural hazards
    at a specific latitude and longitude using a spatial query.
    """
    # FEMA's official ArcGIS REST API Endpoint for the National Risk Index (Census Tracts)
    url = "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Census_Tracts/FeatureServer/0/query"
    
    # Standard Esri ArcGIS spatial query parameters
    params = {
        "geometry": f"{longitude},{latitude}",  # ArcGIS requires Longitude, Latitude order
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",                         # Spatial Reference 4326 is standard GPS coords (WGS84)
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",                       # Return all available data fields
        "returnGeometry": "false",              # We just want the data, not the polygon shape data
        "f": "json"                             # Return as JSON
    }
    
    try:
        # print(f"Fetching FEMA Environmental Risk data for Lat: {latitude}, Lon: {longitude}...\n")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if features were returned (Ensure the coordinates are within the US/Territories)
        if "features" not in data or len(data["features"]) == 0:
            print("No risk data found. This API only covers the United States and its territories.")
            return None
            
        # Extract the attributes (the actual data columns) from the returned feature
        attributes = data["features"][0].get("attributes", {})
        
        # General Information
        county = attributes.get("COUNTY", "Unknown")
        state = attributes.get("STATE", "Unknown")
        overall_risk = attributes.get("RISK_RATNG", "Unknown")
        
        # print(f"--- Environmental Risk Report: {county} County, {state} ---")
        # print(f"Overall National Risk Index:  {overall_risk}")
        # print("-" * 55)
        
        # FEMA uses specific 4-letter abbreviations for their hazard ratings
        hazards = {
            "Wildfire": attributes.get("WLF_RATNG", "Data Unavailable"),
            "Drought": attributes.get("DRGT_RATNG", "Data Unavailable"),
            "Hurricane (Storm)": attributes.get("HRCN_RATNG", "Data Unavailable"),
            "Landslide": attributes.get("LNDS_RATNG", "Data Unavailable"),
            "Coastal Flooding": attributes.get("CFLD_RATNG", "Data Unavailable"), # Sea Level / Coastal
            "River/Inland Flooding": attributes.get("RFLD_RATNG", "Data Unavailable"),
            "Tornado": attributes.get("TRND_RATNG", "Data Unavailable"),
            "Earthquake": attributes.get("ERQK_RATNG", "Data Unavailable"),
            "Winter Weather": attributes.get("WNTW_RATNG", "Data Unavailable"),
            "Heat Wave": attributes.get("HWAV_RATNG", "Data Unavailable")
        }

        # print("-" * 55)
        return hazards

    except requests.exceptions.RequestException as e:
        print(f"Error fetching environmental risk data: {e}")
        return None


# if __name__ == "__main__":
#     test_lat = 38.9187
#     test_lon = -77.2311
#     get_environmental_risk(test_lat, test_lon)