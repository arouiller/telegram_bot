"""
Callback Handlers - Gestiona eventos de botones inline de Telegram.
"""

from src.bot import bot
from src.logger import logger


# ============================================================
# HANDLER: Callback - Registrar entrenamiento
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "registrar_entrenamiento")
def handle_registrar_entrenamiento(call):
    """Maneja click en botón registrar entrenamiento."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    logger.info(f"💪 User {user_id} registrando entrenamiento en chat {chat_id}")

    try:
        bot.answer_callback_query(
            call.id,
            "✅ Has seleccionado registrar entrenamiento",
            show_alert=False
        )

        bot.send_message(
            chat_id,
            "💪 Registrar entrenamiento\n\n"
            "Por favor, describe tu entrenamiento:\n"
            "• Tipo de ejercicio\n"
            "• Duración\n"
            "• Intensidad"
        )

    except Exception as e:
        logger.error(f"❌ Error en handle_registrar_entrenamiento: {str(e)}")
        bot.answer_callback_query(
            call.id,
            "❌ Error procesando tu solicitud",
            show_alert=True
        )


# ============================================================
# HANDLER: Callback - Ver entrenamientos
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "ver_entrenamientos")
def handle_ver_entrenamientos(call):
    """Maneja click en botón ver entrenamientos."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    logger.info(f"📋 User {user_id} viendo entrenamientos en chat {chat_id}")

    try:
        bot.answer_callback_query(
            call.id,
            "✅ Has seleccionado ver entrenamientos",
            show_alert=False
        )

        bot.send_message(
            chat_id,
            "📋 Tus entrenamientos:\n\n"
            "(Funcionalidad de entrenamientos próximamente)"
        )

    except Exception as e:
        logger.error(f"❌ Error en handle_ver_entrenamientos: {str(e)}")
        bot.answer_callback_query(
            call.id,
            "❌ Error procesando tu solicitud",
            show_alert=True
        )