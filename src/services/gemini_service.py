"""
Servicio Gemini - Wrapper de alto nivel para agentes de geografía y voz.
Utiliza AgentOrchestrator para una ejecución centralizada.
"""

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY
from src.logger import logger
from src.services.agent_orchestrator import orchestrator

client = genai.Client(api_key=GEMINI_API_KEY)


def obtener_capital(pais: str) -> str:
    """Consulta la capital de un país específico."""
    capitales = {"Francia": "París", "Japón": "Tokio", "Argentina": "Buenos Aires"}
    return capitales.get(pais, "Capital desconocida")


def obtener_pais(capital: str) -> str:
    """Consulta el país de una capital específica."""
    capitales = {"Francia": "París", "Japón": "Tokio", "Argentina": "Buenos Aires"}
    for pais, cap in capitales.items():
        if cap == capital:
            return pais
    return "País desconocido"


def transcribir_audio_bytes(audio_bytes):
    """Transcribe audio en bytes usando el agente de voz."""
    try:
        prompt = "Transcribe este audio en español. Devuelve únicamente la transcripción."

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/ogg"
                )
            ]
        )
        return response.text
    except Exception as e:
        logger.error(f"Error transcribiendo audio bytes: {str(e)}")
        raise


def transcribir_audio(audio_path: str) -> str:
    """Transcribe audio desde archivo usando el agente de voz."""
    try:
        archivo = client.files.upload(file=audio_path)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Transcribe este audio en español. Devuelve únicamente la transcripción.",
                archivo
            ]
        )
        return response.text
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {str(e)}")
        raise


def consultar_capitales(pais: str) -> str:
    """
    Consulta información sobre capitales usando el agente de geografía.
    Ahora utiliza AgentOrchestrator para ejecución centralizada.
    """
    try:
        prompt = f"¿Cuál es la capital de {pais}? Si no sabes, indica que no está en tu base de datos."
        result = orchestrator.run_agent_sync("geography", prompt)
        return result
    except Exception as e:
        error_msg = f"Error al procesar la solicitud: {str(e)}"
        logger.error(error_msg)
        return error_msg