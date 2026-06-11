# src/services/voice_agent_service.py

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY

from src.services.expense_service import (
    crear_gasto_pendiente,
    obtener_gasto_pendiente,
    confirmar_gasto,
    cancelar_gasto,
    actualizar_categoria
)

from src.services.geography_service import (
    obtener_capital,
    obtener_pais
)

client = genai.Client(
    api_key=GEMINI_API_KEY
)


def procesar_audio_con_tools(
    audio_bytes: bytes,
    user_id: int
) -> str:

    transcripcion = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            """
            Transcribe exactamente el audio.
            Devuelve únicamente la transcripción.
            No expliques ni interpretes.
            """,
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ]
    ).text.strip()

    prompt = f"""
Usuario dijo:

{transcripcion}

Si el mensaje es una consulta de geografía responde directamente.

Si el usuario quiere registrar un gasto:
Extrae:
- descripción
- monto

Devuelve únicamente:

GASTO|descripcion|monto

Ejemplos:

GASTO|Carrefour|15000

Si no es un gasto, responde normalmente.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    texto = response.text.strip()

    if texto.startswith("GASTO|"):

        partes = texto.split("|")

        descripcion = partes[1]
        monto = float(partes[2])

        categoria = crear_gasto_pendiente(
            user_id,
            descripcion,
            monto
        )

        return (
            f"Detecté un gasto.\n\n"
            f"Descripción: {descripcion}\n"
            f"Monto: ${monto:.2f}\n"
            f"Categoría sugerida: "
            f"{categoria}\n\n"
            f"¿Deseas registrarlo?"
        )
    
    pendiente = obtener_gasto_pendiente(user_id)
    if pendiente and texto.lower() in [
        "confirmar gasto",
        "ok, confirmar gasto",
        "sí, confirmar gasto",
        "registrar gasto"
    ]:
        return confirmar_gasto(user_id)

    if pendiente and texto.lower() in [
        "no, cancelar gasto",
        "cancelar gasto",
        "no, cancelar",
        "cancelar"
    ]:
        return cancelar_gasto(user_id)

    if "capital de" in transcripcion.lower():
        pais = (transcripcion.lower().replace("capital de","").strip().title())
        return obtener_capital(pais)

    if "qué país" in transcripcion.lower():
        palabras = transcripcion.split()
        capital = palabras[-1]
        return obtener_pais(capital)

    return texto