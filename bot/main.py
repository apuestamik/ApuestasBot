import os
import logging
import threading
from datetime import datetime, timedelta
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# Configuración básica
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
GOOGLE_SHEET_ID = os.environ['GOOGLE_SHEET_ID']
GOOGLE_CREDS_JSON = os.environ['GOOGLE_CREDS_JSON']

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Inicializar bot
bot = Bot(token=TOKEN)

# Configuración Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# Funciones
def get_next_bet():
    try:
        data = sheet.get_all_records()
        if data:
            bet = data[0]
            partido = bet['Partido']
            cantidad = bet['Cantidad']
            cuota = bet['Cuota']
            hora = bet['Hora']
            return partido, cantidad, cuota, hora
        else:
            return None, None, None, None
    except Exception as e:
        logging.error(f"Error obteniendo datos de Google Sheets: {e}")
        return None, None, None, None

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Hola! Bot listo para comandos.")

def next_bet(update: Update, context: CallbackContext):
    partido, cantidad, cuota, hora = get_next_bet()
    if partido:
        mensaje = f"🎯 Próxima apuesta: {partido}, {cantidad}, cuota {cuota}, {hora}"
    else:
        mensaje = "⚠️ No hay próxima apuesta registrada en el Google Sheet."
    update.message.reply_text(mensaje)

def status(update: Update, context: CallbackContext):
    try:
        data = sheet.get_all_records()
        if data:
            mensaje = "📊 Estado actual de apuestas:\n"
            for row in data:
                mensaje += f"{row['Partido']} - {row['Cantidad']} - cuota {row['Cuota']} - {row['Hora']}\n"
        else:
            mensaje = "📊 No hay apuestas registradas en el Google Sheet."
    except Exception as e:
        mensaje = f"❌ Error al obtener el estado: {e}"
    update.message.reply_text(mensaje)

def send_alerts():
    while True:
        partido, cantidad, cuota, hora = get_next_bet()
        if partido and hora:
            try:
                fight_time = datetime.strptime(hora, "%H:%M").replace(
                    year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
                )
                now = datetime.now()
                if fight_time < now:
                    fight_time += timedelta(days=1)  # Ajusta si la hora ya pasó hoy

                delta_2h = fight_time - timedelta(hours=2)
                delta_30m = fight_time - timedelta(minutes=30)

                # Espera hasta las alertas
                while datetime.now() < delta_2h:
                    time.sleep(60)
                bot.send_message(chat_id=CHAT_ID, text=f"⏰ La pelea '{partido}' es en 2 horas. Prepara el cash out.")
                
                while datetime.now() < delta_30m:
                    time.sleep(60)
                bot.send_message(chat_id=CHAT_ID, text=f"🔥 Última alerta! '{partido}' comienza en 30 minutos.")
            except Exception as e:
                logging.error(f"Error en las alertas: {e}")
        time.sleep(300)  # Revisa cada 5 minutos

# Configurar comandos
updater = Updater(token=TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("next", next_bet))
dp.add_handler(CommandHandler("status", status))

# Iniciar alertas en hilo separado
alert_thread = threading.Thread(target=send_alerts)
alert_thread.daemon = True
alert_thread.start()

# Iniciar bot
updater.start_polling()
updater.idle()