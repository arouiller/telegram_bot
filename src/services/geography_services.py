"""
Geography Services - Herramientas y lógica para consultas de geografía.
Proporciona funciones para obtener capitales y países.
"""

from src.logger import logger

# Datos centralizados de capitales
CAPITALES = {
    "Francia": "París",
    "Japón": "Tokio",
    "Argentina": "Buenos Aires"
}


def obtener_capital(pais: str) -> str:
    """
    Tool: Obtiene la capital de un país.

    Args:
        pais: Nombre del país

    Returns:
        Nombre de la capital del país
    """
    logger.info(f"📍 Buscando capital de {pais}")
    return CAPITALES.get(pais, "Capital desconocida")


def obtener_pais(capital: str) -> str:
    """
    Tool: Obtiene el país de una capital.

    Args:
        capital: Nombre de la capital

    Returns:
        Nombre del país
    """
    logger.info(f"📍 Buscando país para capital {capital}")
    for pais, cap in CAPITALES.items():
        if cap.lower() == capital.lower():
            return pais
    return "País desconocido"
