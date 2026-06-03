import telebot
from telebot import types

# Token for the Telegram bot
TOKEN = '8852894730:AAGQxmUErRvv72Tmkx_KqSW0XRjSn3yg934'

# Initialize the bot with the token
bot = telebot.TeleBot(TOKEN)

# Creacion de comandos simples
# Comando /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! Soy tu bot de Telegram. ¿En qué puedo ayudarte?")

# Comando /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = "Aquí están los comandos disponibles:\n"
    help_text += "/start - Iniciar el bot\n"
    help_text += "/help - Mostrar esta ayuda\n"
    bot.reply_to(message, help_text)

# Comando /entrenamiento
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'entrenamiento')
def send_training_options(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_registrar_entrenamiento = types.InlineKeyboardButton("Registrar entrenamiento", callback_data="registrar_entrenamiento")
    btn_ver_entrenamientos = types.InlineKeyboardButton("Ver entrenamientos", callback_data="ver_entrenamientos")

    markup.add(btn_registrar_entrenamiento, btn_ver_entrenamientos)
    bot.send_message(message.chat.id, "¿Qué te gustaría hacer?", reply_markup=markup)

# Comando /foto
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'foto')
def send_photo(message):
    img_url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/500px-Python-logo-notext.svg.png'
    bot.send_photo(message.chat.id, img_url, caption="Aquí tienes una foto de ejemplo.")

# Comando /echo
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# Manejo de callbacks para los botones
@bot.callback_query_handler(func=lambda call: call.data == "registrar_entrenamiento")
def handle_registrar_entrenamiento(call):
    bot.answer_callback_query(call.id, "Has seleccionado registrar entrenamiento.")

@bot.callback_query_handler(func=lambda call: call.data == "ver_entrenamientos")
def handle_ver_entrenamientos(call):
    bot.answer_callback_query(call.id, "Has seleccionado ver entrenamientos.")

# Iniciar el bot 
if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)