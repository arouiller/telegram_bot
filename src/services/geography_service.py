# src/services/geography_service.py

def obtener_capital(
    pais: str
) -> str:

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

    capitales = {
        "Argentina": "Buenos Aires",
        "Francia": "París",
        "Japón": "Tokio"
    }

    for pais, cap in capitales.items():

        if cap.lower() == capital.lower():
            return pais

    return "País desconocido"