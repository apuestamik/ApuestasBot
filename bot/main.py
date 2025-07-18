import logging
import os
import time
from datetime import datetime, timedelta
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot Token y Chat ID desde Heroku Config Vars
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", SCOPE)
client = gspread.authorize(CREDS)

# ID de Google Sheet
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME = "Hoja 1"
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Zona horaria
TZ = pytz.timezone("America/Mexico_City")

def get_next_bet():
    """Obtiene la próxima apuesta desde Google Sheets"""
    data = sheet.get_all_values()
    if len(data) < 2:
        return None
    partido, cantidad, cuota, hora = data[1]
    return {
        "partido": partido,
        "cantidad": cantidad,
        "cuota": cuota,
        "hora": hora
    }

def send_notification(bot, text):
    """Envía mensaje al chat"""
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info("Notificación enviada")
    except Exception as e:
        logger.error(f"Error enviando notificación: {e}")

def check_and_notify(bot):
    """Verifica el horario y envía notificaciones"""
    bet = get_next_bet()
    if bet:
        hora_apuesta = datetime.strptime(bet["hora"], "%H:%M").replace(
            year=datetime.now(TZ).year,
            month=datetime.now(TZ).month,
            day=datetime.now(TZ).day,
            tzinfo=TZ
        )

        ahora = datetime.now(TZ)
        diff = (hora_apuesta - ahora).total_seconds()

        if 7200 <= diff <= 7500:  # 2 horas antes
            send_notification(bot, f"⏰ Recuerda: {bet['partido']} comienza en 2 horas.")
        elif 1800 <= diff <= 2100:  # 30 minutos antes
            send_notification(bot, f"⚠️ Alerta: {bet['partido']} comienza en 30 minutos.")
        elif 0 <= diff <= 60:  # justo en la hora
            send_notification(bot, f"🔥 La pelea {bet['partido']} está por comenzar!")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Hola! Bot listo para comandos.")

def next_bet(update: Update, context: CallbackContext):
    bet = get_next_bet()
    if bet:
        update.message.reply_text(
            f"🎯 Próxima apuesta:\n"
            f"Partido: {bet['partido']}\n"
            f"Cantidad: {bet['cantidad']}\n"
            f"Cuota: {bet['cuota']}\n"
            f"Hora: {bet['hora']}"
        )
    else:
        update.message.reply_text("📭 No hay apuestas programadas.")

def main():
    bot = Bot(TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next_bet))

    updater.start_polling()

    logger.info("Bot iniciado y monitoreando notificaciones")
    while True:
        check_and_notify(bot)
        time.sleep(60)  # checar cada minuto

if __name__ == '__main__':
    main()