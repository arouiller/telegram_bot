# src/services/geography_service.py

def obtener_capital(
    pais: str
) -> str:
    """
    Obtiene la capital de un país específico.

    Args:
        pais: El nombre del país.

    Returns:
        El nombre de la capital del país, o un mensaje de error si no se encuentra.
    """

    capitales = {
        "Argentina": "Buenos Aires",
        "Francia": "París",
        "Japón": "Tokio"
    }

    return capitales.get(
        pais,
        "Capital desconocida"
    )


def obtener_pais(
    capital: str
) -> str:
    """
    Obtiene el país de una capital específica.

    Args:
        capital: El nombre de la capital.

    Returns:
        El nombre del país, o un mensaje de error si no se encuentra.
    """

    capitales = {
        "Argentina": "Buenos Aires",
        "Francia": "París",
        "Japón": "Tokio"
    }

    for pais, cap in capitales.items():

        if cap.lower() == capital.lower():
            return pais

    return "País desconocido"