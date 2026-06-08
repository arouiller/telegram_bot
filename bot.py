from flask import Flask, request
import telebot
import requests
from telebot import types
from google.adk import Agent
from google.adk.runners import Runner
from google.adk import Task
import os


app = Flask(__name__)

# Telegram
TOKEN = "8852894730:AAGQxmUErRvv72Tmkx_KqSW0XRjSn3yg934"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

#Clima
API_KEY = '9a46e7f26dc8dac780cd81008a3eb3fa'
WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather?'

#Gemini
GEMINI_API_KEY = 'AIzaSyC9n8sXo2m1Zt3v5j8k9l0m1n2o3p4q5r6s7t8u9v0w1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7f8g9h0i1j2k3l4m5n6o7p8q9r0s1t2u3v4w5x6y7z8a9b0c1d2e3f4g5h6i7j8k9l0m1n2o3p4q5r6s7t8u9v0w1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7f8g9h0i1j2k3l4m5'
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# 1. Define una herramienta personalizada
def obtener_capital(pais: str) -> str:
    """Consulta la capital de un país específico."""
    capitales = {"Francia": "París", "Japón": "Tokio", "Argentina": "Buenos Aires"}
    return capitales.get(pais, "Capital desconocida")

# 2. Crea el agente con su perfil, modelo y herramientas
def consultar_agente():
    mi_agente = Agent(
        name="Asistente_Geográfico",
        model="gemini-2.0-flash",
        #model="gemini-1.5-pro", # Puedes especificar otros modelos
        tools=[obtener_capital],
        instruction="Eres un asistente experto en geografía. Usa tus herramientas cuando sea necesario."
    )

    # 3. Ejecuta el agente con un objetivo
    tarea = Task(agent=mi_agente, prompt="Hola, ¿cuál es la capital de Francia y qué país tiene a Buenos Aires como capital?")
    
    resultado = tarea.run()
    return str(resultado.output)


# Latitud y longitud de Cerrito, Argentina
LATITUDE = -31.58044
LONGITUDE = -60.07581

#funcion para obtener el clima actual
def get_weather(latitude, longitude):
    complete_url = WEATHER_URL + "lat=" + str(latitude) + "&lon=" + str(longitude) + "&appid=" + API_KEY + "&units=metric&lang=es"
    response = requests.get(complete_url)
    data = response.json()
    
    if data["cod"] != "404":
        main = data["main"]
        temperature = main["temp"]
        humidity = main["humidity"]
        weather_desc = data["weather"][0]["description"]
        return f"Temperatura: {temperature}°C\nHumedad: {humidity}%\nDescripción: {weather_desc}"
    elif data["cod"] == "401":
        return data["message"]
    else:
        return "No se pudo obtener el clima."   

# Initialize the bot with the token
bot = telebot.TeleBot(TOKEN, threaded=False )

# Creacion de comandos simples

# Comando /clima
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'clima')
def send_weather(message):
    weather_info = get_weather(LATITUDE, LONGITUDE)
    bot.reply_to(message, weather_info)

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

#Comando /gemini
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'gemini')
def send_gemini_options(message):
    help_text = "Esta es la respuesta de gemini:\n"
    help_text += consultar_agente()
    bot.reply_to(message, help_text)    

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


# 🌐 RUTA DEL WEBHOOK (Para Nginx)
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    # Obtener el JSON crudo que envía Telegram
    json_string = request.get_data().decode('utf-8')

    # Transformar el JSON en un objeto "Update" de Telebot
    update = telebot.types.Update.de_json(json_string)

    # Procesar el update (Telebot buscará automáticamente qué manejador debe ejecutar)
    bot.process_new_updates([update])

    return "ok", 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
