import os
import logging
import pytz
import gspread
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from oauth2client.service_account import ServiceAccountCredentials

# Configuración básica
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Zona horaria de Ciudad de México
CDMX_TZ = pytz.timezone("America/Mexico_City")

# Variables de entorno
SHEET_CREDS = os.getenv("SHEET_CREDS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(eval(SHEET_CREDS), scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_SHEET_NAME)

# Obtener peleas activas desde la hoja
def get_fights():
    data = sheet.get_all_records()
    fights = []
    now = datetime.now(CDMX_TZ)

    for row in data:
        try:
            if row["Estatus"].lower() != "activa":
                continue
            pelea = row["Pelea"]
            fecha = row["Fecha"]
            hora = row["Hora (CDMX)"]
            fight_time_str = f"{fecha} {hora}"
            fight_time = CDMX_TZ.localize(datetime.strptime(fight_time_str, "%Y-%m-%d %H:%M"))
            time_diff = (fight_time - now).total_seconds()
            if time_diff > 0:
                fights.append({
                    "pelea": pelea,
                    "hora": fight_time,
                    "tiempo_faltante": time_diff
                })
        except Exception as e:
            logging.error(f"Error procesando fila: {e}")

    return sorted(fights, key=lambda x: x["hora"])

# Enviar alerta al canal
def send_alert(pelea, tiempo):
    mensaje = f"🥊 *Alerta de pelea:* {pelea}\n📍 *Tiempo restante:* {tiempo}\n\n⚠️ ¡Verifica en Betsson! Posible cash out disponible en los próximos 5 minutos."
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensaje, parse_mode="Markdown")

# Verificar si hay peleas próximas y notificar
def check_and_notify():
    fights = get_fights()
    now = datetime.now(CDMX_TZ)

    for f in fights:
        minutos = int(f["tiempo_faltante"] // 60)
        if minutos in [120, 30, 10]:  # 2h, 30min, 10min antes
            send_alert(f["pelea"], f"{minutos} minutos")

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot de apuestas activado y listo para enviar notificaciones.")

# Comando /status
def status(update: Update, context: CallbackContext):
    fights = get_fights()
    if not fights:
        update.message.reply_text("No hay peleas activas registradas.")
    else:
        mensaje = "*Peleas activas:*\n"
        for f in fights:
            hora_str = f["hora"].strftime("%Y-%m-%d %H:%M")
            mensaje += f"- {f['pelea']} a las {hora_str} hora CDMX\n"
        update.message.reply_text(mensaje, parse_mode="Markdown")

# Comando /next
def next_fight(update: Update, context: CallbackContext):
    fights = get_fights()
    if not fights:
        update.message.reply_text("No hay peleas próximas registradas.")
    else:
        p = fights[0]
        hora_str = p["hora"].strftime("%Y-%m-%d %H:%M")
        mensaje = f"📯 Próxima pelea: {p['pelea']} a las {hora_str} hora CDMX"
        update.message.reply_text(mensaje)

# Comando /help
def help_command(update: Update, context: CallbackContext):
    mensaje = "Comandos disponibles:\n/start – Activar bot\n/status – Ver peleas activas\n/next – Siguiente pelea\n/help – Ver ayuda"
    update.message.reply_text(mensaje)

# Inicializar bot
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("status", status))
dp.add_handler(CommandHandler("next", next_fight))
dp.add_handler(CommandHandler("help", help_command))

# Programar verificación periódica
bot = updater.bot
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_notify, "interval", minutes=1)
scheduler.start()

updater.start_polling()
updater.idle()