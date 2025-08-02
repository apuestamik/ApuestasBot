import logging
import os
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Acceso al Google Sheet
sheet = client.open("Apuestas Telegram").worksheet("Apuestas Telegram")

# Zona horaria de CDMX
CDMX = pytz.timezone("America/Mexico_City")

# Función para convertir hora CDMX a UTC
def cdmx_to_utc(cdmx_time_str):
    try:
        naive_time = datetime.strptime(cdmx_time_str, "%H:%M")
        now = datetime.now(CDMX).date()
        cdmx_time = CDMX.localize(datetime.combine(now, naive_time.time()))
        return cdmx_time.astimezone(pytz.utc)
    except Exception as e:
        logger.error(f"Error al convertir hora: {e}")
        return None

# Función para obtener próximas peleas activas
def get_active_fights():
    data = sheet.get_all_records()
    upcoming_fights = []
    for row in data:
        if row["Estatus"].strip().lower() == "activa":
            fight_time = cdmx_to_utc(row["Hora (CDMX)"])
            if fight_time:
                upcoming_fights.append((row["Pelea"], fight_time, row["Fecha"]))
    return upcoming_fights

# Función para enviar notificaciones
def send_notifications(context: CallbackContext):
    chat_id = context.job.context
    fights = get_active_fights()
    now = datetime.now(pytz.utc)
    for pelea, hora_utc, fecha in fights:
        diff = (hora_utc - now).total_seconds()
        if 0 < diff <= 7200:
            context.bot.send_message(chat_id=chat_id, text=f"⏰ Pelea próxima: {pelea} a las {hora_utc.astimezone(CDMX).strftime('%H:%M')} CDMX\n⚠️ ¡Verifica en Betsson! Posible cash out disponible en los próximos 5 minutos.")

# Comandos
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Bot activo. Recibirás alertas de apuestas.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("/start - Iniciar\n/status - Estado del bot\n/next - Próxima pelea\n/help - Ayuda")

def status(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot en línea y monitoreando peleas activas.")

def next_fight(update: Update, context: CallbackContext):
    fights = get_active_fights()
    if fights:
        pelea, hora_utc, fecha = fights[0]
        hora_cdmx = hora_utc.astimezone(CDMX).strftime('%H:%M')
        update.message.reply_text(f"📅 Próxima pelea: {pelea}\n🕒 Hora: {hora_cdmx} CDMX\n📌 Fecha: {fecha}")
    else:
        update.message.reply_text("📭 No hay peleas activas registradas.")

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    updater = Updater(token)
    dispatcher = updater.dispatcher

    # Comandos
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("next", next_fight))

    # Tareas programadas
    job_queue: JobQueue = updater.job_queue
    job_queue.run_repeating(send_notifications, interval=600, first=10, context=chat_id)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()