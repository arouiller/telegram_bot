# src/services/voice_agent_service.py

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY

client = genai.Client(
    api_key=GEMINI_API_KEY
)

def obtener_capital(pais: str) -> str:
    capitales = {
        "Francia": "París",
        "Japón": "Tokio",
        "Argentina": "Buenos Aires"
    }

    return capitales.get(
        pais,
        "Capital desconocida"
    )

def obtener_pais(capital: str) -> str:
    capitales = {
        "Francia": "París",
        "Japón": "Tokio",
        "Argentina": "Buenos Aires"
    }

    for pais, cap in capitales.items():
        if cap == capital:
            return pais

    return "País desconocido"


def procesar_audio_con_tools(audio_bytes):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction="""
            Eres un asistente de Telegram.
            Escucha el audio.
            Usa herramientas cuando sea necesario.
            Si el usuario pregunta por la capital de un país, usa la herramienta obtener_capital.
            Si el usuario pregunta por el país de una capital, usa la herramienta obtener_pais.
            Si el usuario hace una pregunta que no puede ser respondida con las herramientas, responde "Desconozco la respuesta".

            Responde siempre en español.
            """,
            tools=[
                obtener_capital,
                obtener_pais
            ]
        )
    )

    return response.text