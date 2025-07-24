import logging
import os
import time
import gspread
import pytz
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.update import Update

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciales y configuraciones
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GOOGLE_SHEET_NAME = "Apuestas"
TIMEZONE = pytz.timezone("America/Mexico_City")

# Autenticación con Google Sheets
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    return sheet

# Formato de mensaje
def format_alert(fight, time_str):
    return f"""📣 *ALERTA DE APUESTA*

🥊 Pelea: *{fight}*
⏰ Empieza en {time_str}
⚠️ ¡Verifica en Betsson! Posible cash out disponible en los próximos 5 minutos."""

# Enviar mensaje a Telegram
def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Bot de apuestas activado. Te avisaré antes de cada pelea.")

# Comando /help
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("/start - Activar bot\n/next - Próximas peleas\n/status - Ver estado")

# Comando /status
def status(update: Update, context: CallbackContext):
    sheet = get_sheet()
    rows = sheet.get_all_records()
    active = [row for row in rows if row["Estatus"].strip().lower() == "activa"]
    if not active:
        update.message.reply_text("No hay apuestas activas.")
        return
    msg = "📋 *Apuestas Activas:*\n"
    for row in active:
        msg += f"\n🥊 {row['Pelea']} - {row['Fecha']} a las {row['Hora (CDMX)']} - Cuota: {row['Cuota']}"
    update.message.reply_text(msg, parse_mode="Markdown")

# Comando /next
def next(update: Update, context: CallbackContext):
    now = datetime.now(TIMEZONE)
    sheet = get_sheet()
    rows = sheet.get_all_records()
    upcoming = []
    for row in rows:
        if row["Estatus"].strip().lower() != "activa":
            continue
        fight_time = TIMEZONE.localize(datetime.strptime(f"{row['Fecha']} {row['Hora (CDMX)']}", "%Y-%m-%d %H:%M"))
        if fight_time > now:
            upcoming.append((fight_time, row["Pelea"]))
    upcoming.sort()
    if not upcoming:
        update.message.reply_text("No hay próximas peleas.")
        return
    next_fight = upcoming[0]
    update.message.reply_text(f"⏭️ Próxima pelea: {next_fight[1]} a las {next_fight[0].strftime('%H:%M %p')}", parse_mode="Markdown")

# Revisión periódica de alertas
def check_alerts():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    now = datetime.now(TIMEZONE)

    for row in rows:
        if row["Estatus"].strip().lower() != "activa":
            continue
        try:
            fight_time = TIMEZONE.localize(datetime.strptime(f"{row['Fecha']} {row['Hora (CDMX)']}", "%Y-%m-%d %H:%M"))
        except Exception as e:
            logger.warning(f"Error con pelea: {row['Pelea']}, error: {e}")
            continue

        time_diff = (fight_time - now).total_seconds()

        # Tiempos de alerta: 2 horas, 30 minutos, 10 minutos antes
        alerts = {
            7200: "2 horas",
            1800: "30 minutos",
            600: "10 minutos"
        }

        for seconds, label in alerts.items():
            if abs(time_diff - seconds) < 30:  # 30 segundos de margen
                message = format_alert(row["Pelea"], label)
                send_telegram_message(message)

# Main loop
def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("next", next))

    updater.start_polling()

    logger.info("Bot corriendo...")

    while True:
        try:
            check_alerts()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error en main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()