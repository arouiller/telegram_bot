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
# TOOLS PURAS (sin estado)
# =====================================================

def get_clima_local():
    return get_weather(
        latitud=LATITUDE,
        longitud=LONGITUDE
    )


def transcribir_audio(audio_bytes: bytes) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            "Transcribe exactamente el audio sin interpretar.",
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ]
    )
    return response.text.strip()


# =====================================================
# TOOL EXECUTOR (solo tools reales)
# =====================================================

def ejecutar_tools(response):

    candidate = response.candidates[0]

    if not candidate.content.parts:
        return response.text

    for part in candidate.content.parts:

        fc = getattr(part, "function_call", None)
        if not fc:
            continue

        name = fc.name
        args = dict(fc.args)

        logger.info(f"Tool llamada: {name} args={args}")

        if name == "get_clima_local":
            result = get_clima_local()

        elif name == "obtener_capital":
            result = obtener_capital(**args)

        elif name == "obtener_pais":
            result = obtener_pais(**args)

        else:
            result = "Tool no soportada"

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
# INTENCIÓN DE GASTOS (NO TOOL)
# =====================================================

def procesar_gasto(texto: str, user_id: int):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""
Extrae información del siguiente mensaje:

{texto}

Si es un gasto devuelve EXACTAMENTE:
GASTO|descripcion|monto

Ejemplo:
GASTO|cafe|5000

Si no es un gasto responde:
NORMAL|...
"""
    )

    resultado = response.text.strip()

    if resultado.startswith("GASTO|"):

        _, descripcion, monto = resultado.split("|")
        monto = float(monto)

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

    return resultado.replace("NORMAL|", "")


# =====================================================
# CONFIRMACIÓN DE GASTOS
# =====================================================

def procesar_confirmacion(texto: str, user_id: int):

    texto = texto.lower().strip()

    pendiente = obtener_gasto_pendiente(user_id)

    if not pendiente:
        return "No hay gastos pendientes."

    if texto in ["si", "sí", "confirmar", "ok"]:
        return confirmar_gasto(user_id)

    if texto in ["no", "cancelar"]:
        return cancelar_gasto(user_id)

    categorias = [
        "viveres",
        "transporte",
        "servicios",
        "entretenimiento",
        "tecnologia",
        "salud",
        "educacion",
        "otros"
    ]

    for cat in categorias:
        if cat in texto:
            actualizar_categoria(user_id, cat.title())
            return f"Categoría actualizada a {cat.title()}.\n¿Confirmas el gasto?"

    return "Responde: confirmar, cancelar o una categoría."


# =====================================================
# ORQUESTADOR PRINCIPAL
# =====================================================

def procesar_audio_con_tools(audio_bytes: bytes, user_id: int):

    estado = obtener_estado(user_id)["estado"]

    texto = transcribir_audio(audio_bytes)

    logger.info(f"Estado={estado} Texto={texto}")

    # -----------------------------------------
    # IDLE
    # -----------------------------------------
    if estado == ESTADO_IDLE:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=texto,
            config=types.GenerateContentConfig(
                tools=[
                    obtener_capital,
                    obtener_pais,
                    get_clima_local
                ]
            )
        )

        tool_result = ejecutar_tools(response)

        # Si no fue tool → gastos
        return procesar_gasto(tool_result, user_id)

    # -----------------------------------------
    # CONFIRMACIÓN
    # -----------------------------------------
    if estado == ESTADO_ESPERANDO_CONFIRMACION_GASTO:
        return procesar_confirmacion(texto, user_id)

    return "Estado desconocido"