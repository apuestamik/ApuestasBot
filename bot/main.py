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

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SHEET_URL = os.getenv("SHEET_URL")
SHEET_CREDS = os.getenv("SHEET_CREDS")

# Autenticación con Google Sheets
creds_dict = json.loads(SHEET_CREDS)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(credentials)
sheet = client.open_by_url(SHEET_URL).sheet1

# Zona horaria CDMX
TZ = pytz.timezone("America/Mexico_City")

# Función para obtener la próxima apuesta
def obtener_proxima_apuesta():
    rows = sheet.get_all_values()[1:]  # Saltar encabezado
    ahora = datetime.now(TZ)

    for row in rows:
        if len(row) < 4:
            continue
        partido, cantidad, cuota, hora_str = row
        try:
            hora_apuesta = datetime.strptime(hora_str.strip(), "%H:%M").replace(
                year=ahora.year, month=ahora.month, day=ahora.day, tzinfo=TZ
            )
            if hora_apuesta > ahora:
                return f"🎯 Próxima apuesta:\nPartido: {partido}\nCantidad: {cantidad}\nCuota: {cuota}\nHora: {hora_str}"
        except ValueError:
            continue
    return "No hay apuestas próximas registradas."

# Comandos de Telegram
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Hola! Bot listo para comandos.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("/start - Iniciar\n/next - Ver próxima apuesta\n/status - Estado del bot\n/help - Ayuda")

def next_command(update: Update, context: CallbackContext):
    mensaje = obtener_proxima_apuesta()
    update.message.reply_text(mensaje)

def status_command(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot activo y funcionando correctamente.")

# Envío automático cada minuto
def enviar_apuesta_automatica(bot: Bot):
    ya_enviado = set()
    while True:
        ahora = datetime.now(TZ).strftime("%H:%M")
        rows = sheet.get_all_values()[1:]

        for row in rows:
            if len(row) < 4:
                continue
            partido, cantidad, cuota, hora_str = row
            if hora_str.strip() == ahora and hora_str not in ya_enviado:
                mensaje = f"🎯 Próxima apuesta:\nPartido: {partido}\nCantidad: {cantidad}\nCuota: {cuota}\nHora: {hora_str}"
                bot.send_message(chat_id=CHAT_ID, text=mensaje)
                ya_enviado.add(hora_str)
        time.sleep(60)

# Main
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("next", next_command))
    dp.add_handler(CommandHandler("status", status_command))

    # Lanzar bot
    updater.start_polling()

    # Enviar automáticamente
    enviar_apuesta_automatica(updater.bot)

if __name__ == "__main__":
    main()