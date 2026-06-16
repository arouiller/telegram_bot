"""
Message Handlers - Gestiona eventos de mensajes del bot Telegram.
Utiliza AgentOrchestrator para consultas inteligentes.
"""

import threading
import time
from telebot import types as telebot_types

from src.bot import bot
from src.config import LATITUDE, LONGITUDE
from src.logger import logger
from src.services.service_voice_agent import procesar_audio_inline
from src.services.weather_service import get_weather
from src.services.agent_usage_examples import (
    geography_query,
    list_available_agents,
    get_orchestrator_status
)


# ============================================================
# HANDLER: Mensajes de voz
# ============================================================
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Procesa mensajes de audio/voz."""
    chat_id = message.chat.id
    logger.info(f"🎙️ Handler voz iniciado chat_id={chat_id}")

    try:
        bot.send_message(chat_id, "🎙️ Procesando audio...")

        threading.Thread(
            target=procesar_audio_inline,
            args=(message,),
            daemon=True
        ).start()

        logger.info(f"✅ Thread de audio lanzado para {chat_id}")

    except Exception as e:
        logger.error(f"❌ Error en handle_voice: {str(e)}")
        bot.send_message(chat_id, "Error procesando el audio")


# ============================================================
# HANDLER: Comando /ping
# ============================================================
@bot.message_handler(commands=['ping'])
def ping(message):
    """Ping simple para testear conectividad."""
    chat_id = message.chat.id
    start = time.time()

    try:
        bot.send_message(chat_id, "🏓 pong")
        duration = time.time() - start
        logger.info(f"⏱️ Ping response time: {duration:.3f}s")
    except Exception as e:
        logger.error(f"❌ Error en ping: {str(e)}")


# ============================================================
# HANDLER: Comando /start
# ============================================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Mensaje de bienvenida."""
    chat_id = message.chat.id
    logger.info(f"👋 Usuario iniciando bot chat_id={chat_id}")

    welcome_text = (
        "¡Hola! 👋 Soy tu asistente de IA.\n\n"
        "Puedo ayudarte con:\n"
        "📍 Geografía - Pregúntame sobre capitales\n"
        "🎙️ Voz - Envía audios para transcribir\n"
        "🌤️ Clima - Información meteorológica\n\n"
        "Usa /help para más comandos"
    )

    try:
        bot.send_message(chat_id, welcome_text)
    except Exception as e:
        logger.error(f"❌ Error en send_welcome: {str(e)}")


# ============================================================
# HANDLER: Comando /help
# ============================================================
@bot.message_handler(commands=['help'])
def send_help(message):
    """Muestra ayuda disponible."""
    chat_id = message.chat.id
    logger.info(f"ℹ️ Usuario pidiendo help chat_id={chat_id}")

    help_text = (
        "📖 Comandos disponibles:\n\n"
        "/start - Iniciar el bot\n"
        "/help - Mostrar esta ayuda\n"
        "/ping - Test de conectividad\n"
        "/agents - Ver agentes disponibles\n"
        "/status - Estado del sistema\n"
        "/geografia - Modo geografía\n\n"
        "También puedes:\n"
        "🎙️ Enviar audios para transcribir\n"
        "💬 Hacer consultas de geografía\n"
        "🌤️ Preguntar por el clima"
    )

    try:
        bot.send_message(chat_id, help_text)
    except Exception as e:
        logger.error(f"❌ Error en send_help: {str(e)}")


# ============================================================
# HANDLER: Comando /agents
# ============================================================
@bot.message_handler(commands=['agents'])
def show_agents(message):
    """Muestra los agentes disponibles."""
    chat_id = message.chat.id
    logger.info(f"🤖 Usuario pidiendo agentes chat_id={chat_id}")

    try:
        agents = list_available_agents()
        agents_text = "\n".join([f"• {agent}" for agent in agents])

        response = (
            f"🤖 Agentes disponibles ({len(agents)}):\n\n"
            f"{agents_text}"
        )

        bot.send_message(chat_id, response)
    except Exception as e:
        logger.error(f"❌ Error en show_agents: {str(e)}")
        bot.send_message(chat_id, "Error obteniendo agentes")


# ============================================================
# HANDLER: Comando /status
# ============================================================
@bot.message_handler(commands=['status'])
def show_status(message):
    """Muestra el estado del orquestador."""
    chat_id = message.chat.id
    logger.info(f"📊 Usuario pidiendo status chat_id={chat_id}")

    try:
        status = get_orchestrator_status()
        agent_count = len(status['agents'])
        client_ok = "✅" if status['client_initialized'] else "❌"

        response = (
            f"📊 Estado del Sistema:\n\n"
            f"Agentes activos: {agent_count}\n"
            f"Cliente Gemini: {client_ok}\n"
            f"Status: {'🟢 Operativo' if status['client_initialized'] else '🔴 Error'}"
        )

        bot.send_message(chat_id, response)
    except Exception as e:
        logger.error(f"❌ Error en show_status: {str(e)}")
        bot.send_message(chat_id, "Error obteniendo estado")


# ============================================================
# HANDLER: Comando /geografia
# ============================================================
@bot.message_handler(commands=['geografia'])
def geography_mode(message):
    """Entra en modo geografía."""
    chat_id = message.chat.id
    logger.info(f"📍 Usuario en modo geografía chat_id={chat_id}")

    try:
        bot.send_message(
            chat_id,
            "📍 Modo geografía activado.\n"
            "Pregúntame sobre capitales y países.\n"
            "Ej: ¿Cuál es la capital de Francia?"
        )
    except Exception as e:
        logger.error(f"❌ Error en geography_mode: {str(e)}")


# ============================================================
# HANDLER: Comando /clima
# ============================================================
@bot.message_handler(commands=['clima'])
def send_weather(message):
    """Obtiene información climática."""
    chat_id = message.chat.id
    logger.info(f"🌤️ Usuario pidiendo clima chat_id={chat_id}")

    try:
        bot.send_message(chat_id, "🌤️ Obteniendo información climática...")

        weather_info = get_weather()
        bot.send_message(chat_id, weather_info)

    except Exception as e:
        logger.error(f"❌ Error en send_weather: {str(e)}")
        bot.send_message(chat_id, "❌ Error obteniendo el clima")


# ============================================================
# HANDLER: Consultas de geografía (texto)
# ============================================================
@bot.message_handler(
    func=lambda msg: msg.text and any(
        keyword in msg.text.lower()
        for keyword in ['capital', 'país', 'pais', 'ciudad', 'geografía', 'geografia']
    )
)
def handle_geography_query(message):
    """Maneja consultas sobre geografía."""
    chat_id = message.chat.id
    text = message.text
    logger.info(f"📍 Consulta geografía chat_id={chat_id}: {text[:50]}")

    try:
        bot.send_message(chat_id, "⏳ Consultando agente de geografía...")

        result = geography_query(text)
        bot.send_message(chat_id, result)

    except Exception as e:
        logger.error(f"❌ Error en handle_geography_query: {str(e)}")
        bot.send_message(chat_id, "❌ Error procesando tu consulta")


# ============================================================
# HANDLER: Comando /entrenamiento
# ============================================================
@bot.message_handler(
    func=lambda msg: msg.text and msg.text.lower() == 'entrenamiento'
)
def send_training_options(message):
    """Muestra opciones de entrenamiento."""
    chat_id = message.chat.id
    logger.info(f"💪 Usuario pidiendo opciones entrenamiento chat_id={chat_id}")

    markup = telebot_types.InlineKeyboardMarkup(row_width=2)
    btn_registrar = telebot_types.InlineKeyboardButton(
        "Registrar entrenamiento",
        callback_data="registrar_entrenamiento"
    )
    btn_ver = telebot_types.InlineKeyboardButton(
        "Ver entrenamientos",
        callback_data="ver_entrenamientos"
    )

    markup.add(btn_registrar, btn_ver)

    try:
        bot.send_message(
            chat_id,
            "💪 ¿Qué te gustaría hacer?",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"❌ Error en send_training_options: {str(e)}")


# ============================================================
# HANDLER: Mensaje de echo (default)
# ============================================================
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Echo de mensajes no coincidentes."""
    chat_id = message.chat.id
    text = message.text
    logger.info(f"🔄 Echo message chat_id={chat_id}: {text[:50]}")

    try:
        bot.reply_to(
            message,
            f"Recibí: {text}\n\nUsa /help para ver comandos disponibles"
        )
    except Exception as e:
        logger.error(f"❌ Error en echo_all: {str(e)}")