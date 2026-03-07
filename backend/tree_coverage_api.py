import ee

ee.Initialize(project="rhetorica-464606")

def tree_cover_dynamic_world(min_lon, min_lat, max_lon, max_lat,
                             start_date="2024-01-01",
                             end_date="2024-12-31"):

    # Region of interest
    roi = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

    # Load Dynamic World dataset
    dw = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
    )

    # Dynamic World class labels
    # 1 = trees
    tree_pixels = dw.select("label").map(lambda img: img.eq(1))

    # Average classification across all observations
    tree_fraction = tree_pixels.mean()

    # Pixels classified as trees in >=50% of observations
    tree_mask = tree_fraction.gte(0.5)

    # Calculate tree area
    tree_area = ee.Image.pixelArea().updateMask(tree_mask)

    stats = tree_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=roi,
        scale=10,
        maxPixels=1e13
    )

    tree_area_m2 = ee.Number(stats.get("area"))

    total_area_m2 = roi.area()

    tree_cover_percent = tree_area_m2.divide(total_area_m2).multiply(100)

    return {
        "tree_area_m2": tree_area_m2.getInfo(),
        "tree_area_km2": tree_area_m2.divide(1e6).getInfo(),
        "total_area_m2": total_area_m2.getInfo(),
        "tree_cover_percent": tree_cover_percent.getInfo(),
        "dataset": "Dynamic World",
        "date_range": f"{start_date} to {end_date}"
    }


# Example: Central Park NYC
stats = tree_cover_dynamic_world(
    -73.9819,
    40.7642,
    -73.9498,
    40.8007
)

print(stats)