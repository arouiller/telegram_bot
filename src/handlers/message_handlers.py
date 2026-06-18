"""
Message Handlers - Gestiona eventos de mensajes del bot Telegram.
Utiliza AgentOrchestrator para consultas inteligentes.
"""

import threading
import time
from telebot import types as telebot_types

from src.bot import bot
from src.logger import logger
from src.services.service_voice_agent import procesar_audio


# ============================================================
# HANDLER: Mensajes de voz
# ============================================================
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Procesa mensajes de audio/voz."""
    chat_id = message.chat.id
    logger.info(f"🎙️ Handler voz iniciado chat_id={chat_id}")

    try:
        threading.Thread(
            target=procesar_audio,
            args=(message,),
            daemon=True
        ).start()

        logger.info(f"✅ Thread de audio lanzado para {chat_id}")

    except Exception as e:
        logger.error(f"❌ Error en handle_voice: {str(e)}")
        bot.send_message(chat_id, "Error procesando el audio")


# ============================================================
# HANDLER: Mensaje de echo (default)
# ============================================================
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Echo de mensajes no coincidentes."""
    chat_id = message.chat.id
    start = time.time()

    text = message.text
    logger.info(f"🔄 Echo message chat_id={chat_id}: {text[:50]}")

    try:
        bot.reply_to(
            message,
            f"Recibí: {text}\n\nUsa /help para ver comandos disponibles"
        )
        duration = time.time() - start
        logger.info(f"⏱️ Ping response time: {duration:.3f}s")
    except Exception as e:
        logger.error(f"❌ Error en echo_all: {str(e)}")