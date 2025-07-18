import logging
import os
import time
import json
from datetime import datetime, timedelta
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SHEET_URL = os.getenv("SHEET_URL")
SHEET_CREDS = os.getenv("SHEET_CREDS")

# Google Sheets Auth
creds_dict = json.loads(SHEET_CREDS)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(credentials)
sheet = client.open_by_url(SHEET_URL).sheet1

# Zona horaria
TZ = pytz.timezone("America/Mexico_City")

# Función para obtener próxima apuesta
def obtener_proxima_apuesta():
    rows = sheet.get_all_values()
    if len(rows) < 2:
        return "No hay apuestas registradas."
    
    data = rows[1]
    partido = data[0]
    cantidad = data[1]
    cuota = data[2]
    hora = data[3]
    
    mensaje = f"🎯 Próxima apuesta:\nPartido: {partido}\nCantidad: {cantidad}\nCuota: {cuota}\nHora: {hora}"
    return mensaje

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Hola! Bot listo para comandos.")

# Comando /next
def next_bet(update: Update, context: CallbackContext):
    mensaje = obtener_proxima_apuesta()
    update.message.reply_text(mensaje)

# Comando /help
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("🛠 Comandos disponibles:\n/start - Iniciar bot\n/next - Ver próxima apuesta\n/help - Ayuda\n/status - Estado del bot")

# Comando /status
def status_command(update: Update, context: CallbackContext):
    update.message.reply_text("✅ El bot está funcionando correctamente.")

# Loop principal
def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("next", next_bet))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("status", status_command))

    updater.start_polling()
    logger.info("Bot iniciado.")
    updater.idle()

if __name__ == "__main__":
    main()