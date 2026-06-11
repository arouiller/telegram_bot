import requests

from src.config import OPENWEATHER_API_KEY

WEATHER_URL = (
    "https://api.openweathermap.org/data/2.5/weather"
)


def get_weather(lat, lon):

    response = requests.get(
        WEATHER_URL,
        params={
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "es"
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    main = data["main"]

    return (
        f"Temperatura: {main['temp']}°C\n"
        f"Humedad: {main['humidity']}%\n"
        f"Descripción: {data['weather'][0]['description']}"
    )