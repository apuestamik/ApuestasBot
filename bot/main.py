import logging
import os
import pytz
import gspread
import json
import threading
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Configuración de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Zona horaria de CDMX
tz = pytz.timezone("America/Mexico_City")

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SHEET_URL = os.getenv("SHEET_URL")
SHEET_CREDS = json.loads(os.getenv("SHEET_CREDS"))

# Conectar con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(SHEET_CREDS, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1

# Leer datos de la hoja
def get_apuestas():
    data = sheet.get_all_records()
    return data

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Hola! Bot listo para comandos.")

# Comando /help
def help_command(update: Update, context: CallbackContext):
    help_text = (
        "📋 *Comandos disponibles:*\n"
        "/start - Iniciar bot\n"
        "/help - Ver comandos\n"
        "/next - Ver próxima apuesta\n"
        "/status - Ver apuestas registradas"
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

# Comando /next
def next_command(update: Update, context: CallbackContext):
    apuestas = get_apuestas()
    if not apuestas:
        update.message.reply_text("No hay apuestas registradas.")
        return

    proxima = apuestas[0]
    mensaje = (
        f"🎯 Próxima apuesta:\n"
        f"Partido: {proxima['Partido']}\n"
        f"Cantidad: {proxima['Cantidad']}\n"
        f"Cuota: {proxima['Cuota']}\n"
        f"Hora: {proxima['Hora']}"
    )
    update.message.reply_text(mensaje)

# Comando /status
def status_command(update: Update, context: CallbackContext):
    apuestas = get_apuestas()
    if not apuestas:
        update.message.reply_text("No hay apuestas registradas.")
        return

    mensaje = "📊 Estado actual de apuestas:\n"
    for a in apuestas:
        mensaje += f"{a['Partido']} - {a['Cantidad']} - {a['Cuota']} - {a['Hora']}\n"
    update.message.reply_text(mensaje)

# Notificaciones programadas
def enviar_recordatorios():
    apuestas = get_apuestas()
    if not apuestas:
        return

    proxima = apuestas[0]
    hora_pelea_str = proxima["Hora"]
    hora_objetivo = datetime.strptime(hora_pelea_str, "%H:%M")
    ahora = datetime.now(tz)
    pelea_hoy = ahora.replace(hour=hora_objetivo.hour, minute=hora_objetivo.minute, second=0, microsecond=0)

    notificaciones = [
        pelea_hoy - timedelta(hours=2),
        pelea_hoy - timedelta(minutes=30)
    ]

    for momento in notificaciones:
        delay = (momento - ahora).total_seconds()
        if delay > 0:
            threading.Timer(delay, enviar_alerta, args=(proxima, momento)).start()

def enviar_alerta(apuesta, momento):
    mensaje = (
        f"⏰ *Alerta de apuesta!*\n"
        f"{apuesta['Partido']} inicia pronto.\n"
        f"Cantidad: {apuesta['Cantidad']} - Cuota: {apuesta['Cuota']}\n"
        f"Hora de inicio: {apuesta['Hora']}"
    )
    updater.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensaje, parse_mode='Markdown')

# Iniciar bot
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("next", next_command))
dispatcher.add_handler(CommandHandler("status", status_command))

# Iniciar polling y notificaciones
updater.start_polling()
enviar_recordatorios()
updater.idle()