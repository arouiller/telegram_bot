from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY

client = genai.Client(
    api_key=GEMINI_API_KEY
)

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

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Transcribe este audio en español. Devuelve únicamente la transcripción.",
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ]
    )

    return response.text

def transcribir_audio(audio_path):
    archivo = client.files.upload(
        file=audio_path
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            """
            Transcribe este audio en español.
            Devuelve únicamente la transcripción.
            """,
            archivo
        ]
    )

    return response.text

def consultar_capitales(pais):
    client = genai.Client(api_key=GEMINI_API_KEY)  # Usa la API unificada de Gemini
    INSTRUCCIONES_AGENTE = "Eres un asistente experto en geografía llamado asistente_geografico. Usa tus herramientas si te preguntan capitales."
    try:
        # Ejecutamos la llamada directa usando la API oficial unificada
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Hola, ¿cuál es la capital de Francia y qué país tiene a Buenos Aires como capital?",
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCCIONES_AGENTE,
                tools=[obtener_capital, obtener_pais], # Mapea tu función de Python directamente
                temperature=0.3,
            )
        )
        # Retornamos el texto limpio generado por el modelo
        return response.text
    except Exception as e:
        return f"Error al procesar la solicitud con Gemini: {str(e)}"