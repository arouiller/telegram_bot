import requests

from src.config import OPENWEATHER_API_KEY, LATITUDE, LONGITUDE


WEATHER_URL = (
    "https://api.openweathermap.org/data/2.5/weather"
)


def get_weather():
    """
    Obtiene el clima actual 

    Returns:
        Un string con la información del clima.
    """

    response = requests.get(
        WEATHER_URL,
        params={
            "lat": LATITUDE,
            "lon": LONGITUDE,
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