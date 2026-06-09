from flask import Flask, request
import telebot
import requests
from telebot import types
from google.adk import Agent
from google.adk.runners import Runner
from google import genai
from google.genai import types
import os


app = Flask(__name__)

# Telegram
TOKEN = "8852894730:AAGQxmUErRvv72Tmkx_KqSW0XRjSn3yg934"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

#Clima
API_KEY = '9a46e7f26dc8dac780cd81008a3eb3fa'
WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather?'

#Gemini
GEMINI_API_KEY = 'AQ.Ab8RN6KYIYMjUsytHh-Umm4hXjsDwWL9lfzhDC4tMoQpKrwKqQ'

def transcribir_audio(audio_path):
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        archivo = client.files.upload(
            file=audio_path
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Transcribe este audio en español. Devuelve únicamente la transcripción.",
                archivo
            ]
        )

        return response.text

    except Exception as e:
        return f"Error al transcribir: {str(e)}"

# 1. Define una herramienta personalizada
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

# 2. Crea el agente con su perfil, modelo y herramientas
def consultar_agente():
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
@bot.message_handler(content_types=['voice'])
def handle_voice(message):

    try:

        bot.reply_to(
            message,
            "🎙️ Audio recibido. Transcribiendo..."
        )

        file_info = bot.get_file(message.voice.file_id)

        file_url = (
            f"https://api.telegram.org/file/bot{TOKEN}/"
            f"{file_info.file_path}"
        )

        response = requests.get(file_url)

        os.makedirs("audios", exist_ok=True)

        audio_path = f"audios/{message.voice.file_id}.ogg"

        with open(audio_path, "wb") as audio_file:
            audio_file.write(response.content)

        texto = transcribir_audio(audio_path)

        bot.send_message(
            message.chat.id,
            f"📝 Transcripción:\n\n{texto}"
        )

        os.remove(audio_path)

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Error: {str(e)}"
        )

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
