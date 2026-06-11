from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY

client = genai.Client(
    api_key=GEMINI_API_KEY
)


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