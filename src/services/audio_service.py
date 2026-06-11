import os
import requests

from src.bot import bot
from src.config import TELEGRAM_TOKEN
from src.services.gemini_service import transcribir_audio


def procesar_audio(message):

    try:

        file_info = bot.get_file(
            message.voice.file_id
        )

        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{TELEGRAM_TOKEN}/"
            f"{file_info.file_path}"
        )

        response = requests.get(
            file_url,
            timeout=30
        )

        os.makedirs(
            "audios",
            exist_ok=True
        )

        audio_path = (
            f"audios/{message.voice.file_id}.ogg"
        )

        with open(audio_path, "wb") as audio_file:
            audio_file.write(response.content)

        texto = transcribir_audio(audio_path)

        bot.send_message(
            message.chat.id,
            texto
        )

    except Exception as ex:

        bot.send_message(
            message.chat.id,
            f"Error: {str(ex)}"
        )

    finally:

        if (
            "audio_path" in locals()
            and os.path.exists(audio_path)
        ):
            os.remove(audio_path)