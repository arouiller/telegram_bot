from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY, LATITUDE, LONGITUDE
from src.logger import logger

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

from src.services.weather_service import get_weather

from src.services.conversation_state_service import (
    obtener_estado,
    ESTADO_IDLE,
    ESTADO_ESPERANDO_CONFIRMACION_GASTO
)

client = genai.Client(api_key=GEMINI_API_KEY)


# =====================================================
# TOOLS REALES
# =====================================================

def get_clima_local():
    return get_weather(
        latitud=LATITUDE,
        longitud=LONGITUDE
    )


# =====================================================
# TRANSCRIPCIÓN
# =====================================================

def transcribir_audio(audio_bytes: bytes) -> str:

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            "Transcribe exactamente el audio. No expliques nada.",
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ]
    )

    return response.text.strip()


# =====================================================
# TOOL EXECUTOR (CLAVE DEL SISTEMA)
# =====================================================

def ejecutar_tools(response):

    candidate = response.candidates[0]

    if not candidate.content.parts:
        return response.text

    for part in candidate.content.parts:

        if not getattr(part, "function_call", None):
            continue

        fc = part.function_call
        name = fc.name
        args = dict(fc.args)

        logger.info(f"Tool llamada: {name} args={args}")

        # -----------------------------
        # WEATHER
        # -----------------------------
        if name == "get_clima_local":
            result = get_clima_local()

        # -----------------------------
        # GEOGRAPHY
        # -----------------------------
        elif name == "obtener_capital":
            result = obtener_capital(**args)

        elif name == "obtener_pais":
            result = obtener_pais(**args)

        # -----------------------------
        # EXPENSES
        # -----------------------------
        elif name == "crear_gasto_pendiente":
            result = crear_gasto_pendiente(**args)

        elif name == "confirmar_gasto":
            result = confirmar_gasto(**args)

        elif name == "cancelar_gasto":
            result = cancelar_gasto(**args)

        elif name == "actualizar_categoria":
            result = actualizar_categoria(**args)

        else:
            result = "Tool no soportada"

        # -----------------------------
        # Segunda pasada (respuesta final)
        # -----------------------------
        followup = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                part,
                types.Part.from_text(str(result))
            ]
        )

        return followup.text

    return response.text


# =====================================================
# AGENTE PRINCIPAL
# =====================================================

def procesar_audio_con_tools(audio_bytes: bytes, user_id: int):

    estado = obtener_estado(user_id)
    estado_actual = estado["estado"]

    logger.info(f"Estado actual: {estado_actual}")

    texto = transcribir_audio(audio_bytes)

    # =====================================================
    # ESTADO IDLE
    # =====================================================
    if estado_actual == ESTADO_IDLE:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=texto,
            config=types.GenerateContentConfig(
                tools=[
                    obtener_capital,
                    obtener_pais,
                    get_clima_local,
                    crear_gasto_pendiente
                ]
            )
        )

        return ejecutar_tools(response)

    # =====================================================
    # ESTADO CONFIRMACIÓN GASTO
    # =====================================================
    if estado_actual == ESTADO_ESPERANDO_CONFIRMACION_GASTO:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=texto,
            config=types.GenerateContentConfig(
                tools=[
                    confirmar_gasto,
                    cancelar_gasto,
                    actualizar_categoria
                ]
            )
        )

        return ejecutar_tools(response)

    return "Estado desconocido"