import telebot

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

# Comando /echo
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# Iniciar el bot
if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)