import requests

def get_weather_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m"
        ],
        "timezone": "auto"
    }

    response = requests.get(url, params=params)
    data = response.json()

    return data["current"]


# if __name__ == "__main__":
#     lat = float(input("Latitude: "))
#     lon = float(input("Longitude: "))

#     weather = get_weather_data(lat, lon)

#     print("\nCurrent Weather")
#     print("----------------------")
#     print(f"Time: {weather['time']}")
#     print(f"Temperature: {weather['temperature_2m']} °C")
#     print(f"Feels Like: {weather['apparent_temperature']} °C")
#     print(f"Humidity: {weather['relative_humidity_2m']} %")
#     print(f"Precipitation: {weather['precipitation']} mm")
#     print(f"Wind Speed: {weather['wind_speed_10m']} km/h")
#     print(f"Wind Direction: {weather['wind_direction_10m']}°")
#     print(f"Weather Code: {weather['weather_code']}")