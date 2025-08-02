import os
import logging
import pytz
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot, Update
from telegram.ext import CommandHandler, Updater, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

# Configuración del logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Variables de entorno
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME")
SHEET_CREDS = os.environ.get("SHEET_CREDS")

# Configurar conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(eval(SHEET_CREDS), scope)
client = gspread.authorize(credentials)
sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_SHEET_NAME)

# Zona horaria de Ciudad de México
CDMX_TZ = pytz.timezone("America/Mexico_City")

bot = Bot(token=TELEGRAM_TOKEN)

def get_active_fights():
    data = sheet.get_all_records()
    now = datetime.datetime.now(CDMX_TZ)
    fights = []

    for row in data:
        if row.get("Estatus", "").strip().lower() == "activa":
            fecha = row.get("Fecha")
            hora = row.get("Hora (CDMX)")
            pelea = row.get("Pelea")

            if not fecha or not hora or not pelea:
                continue

            try:
                fight_time_str = f"{fecha} {hora}"
                fight_time = CDMX_TZ.localize(datetime.datetime.strptime(fight_time_str, "%Y-%m-%d %H:%M"))
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

def send_alert(pelea, tiempo):
    mensaje = f"⏰ *Alerta de pelea:* {pelea}"
📍 *Tiempo restante:* {tiempo}

⚠️ ¡Verifica en Betsson! Posible cash out disponible en los próximos 5 minutos."
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensaje, parse_mode="Markdown")

def check_and_notify():
    fights = get_active_fights()
    now = datetime.datetime.now(CDMX_TZ)

    for fight in fights:
        tiempo_restante = (fight["hora"] - now).total_seconds()
        if 7180 < tiempo_restante < 7220:  # 2h antes
            send_alert(fight["pelea"], "2 horas")
        elif 1780 < tiempo_restante < 1820:  # 30 min antes
            send_alert(fight["pelea"], "30 minutos")
        elif 580 < tiempo_restante < 620:  # 10 min antes
            send_alert(fight["pelea"], "10 minutos")

# Comandos de Telegram
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Bot activo. Tendrás alertas de próximas apuestas.")

def status(update: Update, context: CallbackContext):
    peleas = get_active_fights()
    if not peleas:
        update.message.reply_text("No hay peleas activas registradas.")
    else:
        mensaje = "*Peleas activas:*
"
        for p in peleas:
            hora_str = p["hora"].strftime("%Y-%m-%d %H:%M")
            mensaje += f"- {p['pelea']} a las {hora_str} CDMX
"
        update.message.reply_text(mensaje, parse_mode="Markdown")

def next_fight(update: Update, context: CallbackContext):
    peleas = get_active_fights()
    if not peleas:
        update.message.reply_text("No hay peleas activas.")
    else:
        p = peleas[0]
        hora_str = p["hora"].strftime("%Y-%m-%d %H:%M")
        mensaje = f"📢 Próxima pelea:
{p['pelea']} a las {hora_str} hora CDMX"
        update.message.reply_text(mensaje)

def help_command(update: Update, context: CallbackContext):
    mensaje = "Comandos disponibles:
/start - Activar bot
/status - Ver peleas activas
/next - Siguiente pelea
/help - Ver ayuda"
    update.message.reply_text(mensaje)

# Configuración del bot
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("status", status))
dp.add_handler(CommandHandler("next", next_fight))
dp.add_handler(CommandHandler("help", help_command))

# Programar verificación periódica
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_notify, "interval", minutes=1)
scheduler.start()

updater.start_polling()
updater.idle()