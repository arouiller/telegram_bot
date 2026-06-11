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

from src.services.conversation_state_service import (
    obtener_estado,
    ESTADO_IDLE,
    ESTADO_ESPERANDO_CONFIRMACION_GASTO
)

client = genai.Client(
    api_key=GEMINI_API_KEY
)


def transcribir_audio(audio_bytes):

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            """
            Transcribe exactamente el audio.
            Devuelve únicamente la transcripción.
            No expliques.
            No interpretes.
            """,
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ]
    )

    return response.text.strip()


def procesar_estado_idle(
    texto: str,
    user_id: int
):

    prompt = f"""
Usuario dijo:

{texto}

Si quiere registrar un gasto:

Devuelve:

GASTO|descripcion|monto

Ejemplo:

GASTO|Carrefour|15000

Si pregunta una capital:

CAPITAL|pais

Si pregunta el país de una capital:

PAIS|capital

Si no aplica:

NORMAL|respuesta
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    resultado = response.text.strip()

    if resultado.startswith("GASTO|"):

        partes = resultado.split("|")

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
            f"Categoría sugerida: {categoria}\n\n"
            f"¿Deseas registrarlo?"
        )

    if resultado.startswith("CAPITAL|"):

        pais = resultado.split("|")[1]

        return obtener_capital(
            pais
        )

    if resultado.startswith("PAIS|"):

        capital = resultado.split("|")[1]

        return obtener_pais(
            capital
        )

    if resultado.startswith("NORMAL|"):

        return resultado.replace(
            "NORMAL|",
            ""
        )

    return resultado


def procesar_confirmacion_gasto(
    texto: str,
    user_id: int
):

    prompt = f"""
Usuario respondió:

{texto}

Clasifica únicamente como:

CONFIRMAR
CANCELAR
CAMBIAR_CATEGORIA
OTRO

Devuelve una sola palabra.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    accion = response.text.strip().upper()

    if accion == "CONFIRMAR":
        return confirmar_gasto(
            user_id
        )

    if accion == "CANCELAR":
        return cancelar_gasto(
            user_id
        )

    categorias = [
        "Viveres",
        "Transporte",
        "Servicios",
        "Entretenimiento",
        "Tecnologia",
        "Salud",
        "Educacion",
        "Otros"
    ]

    texto_lower = texto.lower()

    for categoria in categorias:

        if categoria.lower() in texto_lower:

            actualizar_categoria(
                user_id,
                categoria
            )

            return (
                f"Categoría actualizada a "
                f"{categoria}.\n\n"
                f"¿Deseas registrarlo?"
            )

    return (
        "No entendí la respuesta.\n\n"
        "Puedes decir:\n"
        "- confirmar\n"
        "- cancelar\n"
        "- una categoría"
    )


def procesar_audio_con_tools(
    audio_bytes: bytes,
    user_id: int
):

    texto = transcribir_audio(
        audio_bytes
    )

    estado = obtener_estado(
        user_id
    )

    estado_actual = estado["estado"]

    if estado_actual == ESTADO_IDLE:

        return procesar_estado_idle(
            texto,
            user_id
        )

    if (
        estado_actual
        == ESTADO_ESPERANDO_CONFIRMACION_GASTO
    ):

        return procesar_confirmacion_gasto(
            texto,
            user_id
        )

    return (
        "Estado desconocido."
    )