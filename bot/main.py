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

# Credenciales de Google Sheets desde variable de entorno
creds_dict = json.loads(SHEET_CREDS)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(credentials)
sheet = client.open_by_url(SHEET_URL).sheet1

# Zona horaria
TZ = pytz.timezone("America/Mexico_City")

def get_next_bet():
    """Obtiene la próxima apuesta desde Google Sheets"""
    data = sheet.get_all_values()
    if len(data) < 2:
        return None
    partido, cantidad, cuota, hora = data[1]
    return {
        "partido": partido.strip(),
        "cantidad": cantidad.strip(),
        "cuota": cuota.strip(),
        "hora": hora.strip()
    }

def send_notification(bot, text):
    """Envía mensaje al chat"""
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info("✅ Notificación enviada: %s", text)
    except Exception as e:
        logger.error("❌ Error enviando notificación: %s", e)

def check_and_notify(bot):
    """Verifica la hora y envía notificaciones"""
    bet = get_next_bet()
    if bet:
        ahora = datetime.now(TZ)
        hora_obj = datetime.strptime(bet["hora"], "%H:%M").replace(
            year=ahora.year, month=ahora.month, day=ahora.day, tzinfo=TZ
        )
        diff = (hora_obj - ahora).total_seconds()

        if 7200 <= diff <= 7260:  # 2h antes
            send_notification(bot, f"⏰ Recuerda: {bet['partido']} comienza en 2 horas.")
        elif 1800 <= diff <= 1860:  # 30 min antes
            send_notification(bot, f"⚠️ Alerta: {bet['partido']} comienza en 30 minutos.")
        elif 0 <= diff <= 60:  # justo en la hora
            send_notification(bot, f"🔥 La pelea {bet['partido']} está por comenzar!")

def start(update: Update, context: CallbackContext):
    """Comando /start"""
    update.message.reply_text("👋 Hola! Bot listo para comandos.")

def next_bet(update: Update, context: CallbackContext):
    """Comando /next"""
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
    """Main loop"""
    bot = Bot(TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next_bet))

    updater.start_polling()
    logger.info("🤖 Bot iniciado y escuchando comandos...")

    while True:
        check_and_notify(bot)
        time.sleep(60)

if __name__ == "__main__":
    main()