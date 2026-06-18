import json
import requests
from pathlib import Path

from src.config import OPENWEATHER_API_KEY, LATITUDE, LONGITUDE
from src.logger import logger

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
CITIES_DB_PATH = Path(__file__).parent.parent.parent.parent / "cities.json"


def get_latitude_and_longitude(localidad: str, provincia: str = None) -> str:
    """
    Obtiene latitud y longitud para una localidad.

    Estrategia híbrida (Opción C):
    1. Busca en BD local (rápido)
    2. Fallback a OpenWeather Geocoding API
    3. Fallback a coordenadas por defecto

    Args:
        localidad: Nombre de la ciudad (ej: "La Plata")
        provincia: Provincia opcional (ej: "Buenos Aires")

    Returns:
        String formateado: "latitud|longitud"
        Ej: "-34.9211|-57.9545"
    """
    try:
        # Paso 1: Intentar BD local (rápido, ~50ms)
        if CITIES_DB_PATH.exists():
            with open(CITIES_DB_PATH, encoding="utf-8") as f:
                cities = json.load(f)

            # Búsqueda exacta por nombre de ciudad
            if localidad in cities:
                data = cities[localidad]
                logger.info(f"📍 Ubicación encontrada en BD local: {localidad}")
                return f"{data['lat']}|{data['lon']}"

            # Búsqueda por provincia si se especifica
            if provincia:
                for city, data in cities.items():
                    if data["province"].lower() == provincia.lower():
                        logger.info(f"📍 Ubicación encontrada por provincia: {city}")
                        return f"{data['lat']}|{data['lon']}"

    except Exception as e:
        logger.warning(f"Error leyendo BD local de ciudades: {str(e)}")

    # Paso 2: Fallback a API OpenWeather Geocoding (~300ms)
    logger.info(f"📍 Buscando ubicación en API: {localidad}")
    try:
        query = f"{localidad}, {provincia}" if provincia else localidad

        response = requests.get(
            GEOCODING_URL,
            params={
                "q": query,
                "limit": 1,
                "appid": OPENWEATHER_API_KEY
            },
            timeout=5
        )

        if response.status_code == 200 and response.json():
            data = response.json()[0]
            logger.info(f"📍 Ubicación encontrada en API: {localidad}")
            return f"{data['lat']}|{data['lon']}"

    except Exception as e:
        logger.error(f"Error en geocoding API: {str(e)}")

    # Paso 3: Fallback a coordenadas por defecto
    logger.warning(f"📍 Ubicación no encontrada, usando coordenadas por defecto")
    return f"{LATITUDE}|{LONGITUDE}"


def get_weather(latitud: float, longitud: float) -> str:
    """
    Obtiene el clima actual para coordenadas específicas.

    Args:
        latitud: Latitud del lugar
        longitud: Longitud del lugar

    Returns:
        String con información climática formateado

    Raises:
        Exception: Si hay error en la API de OpenWeather
    """
    try:
        response = requests.get(
            WEATHER_URL,
            params={
                "lat": latitud,
                "lon": longitud,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang": "es"
            },
            timeout=10
        )

        response.raise_for_status()
        data = response.json()
        main = data["main"]

        logger.info(f"🌤️ Clima obtenido para {data['name']}: {main['temp']}°C")

        return (
            f"Temperatura en {data['name']}: {main['temp']}°C\n"
            f"Humedad: {main['humidity']}%\n"
            f"Descripción: {data['weather'][0]['description']}"
        )

    except Exception as e:
        logger.error(f"Error obteniendo clima: {str(e)}")
        raise