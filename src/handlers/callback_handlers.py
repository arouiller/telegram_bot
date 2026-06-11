# Manejo de callbacks para los botones
import threading

from telebot import types as telebot_types

from src.bot import bot

@bot.callback_query_handler(func=lambda call: call.data == "registrar_entrenamiento")
def handle_registrar_entrenamiento(call):
    bot.answer_callback_query(call.id, "Has seleccionado registrar entrenamiento.")

@bot.callback_query_handler(func=lambda call: call.data == "ver_entrenamientos")
def handle_ver_entrenamientos(call):
    bot.answer_callback_query(call.id, "Has seleccionado ver entrenamientos.")