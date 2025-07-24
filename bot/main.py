import os
import gspread
import pytz
import time
import logging
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from telegram.ext import Updater, CommandHandler

# --- Configuración ---
SPREADSHEET_NAME = "Apuestas Telegram"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Credenciales de Google ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
CLIENT = gspread.authorize(CREDS)

# --- Zona horaria CDMX ---
CDMX_TZ = pytz.timezone("America/Mexico_City")

# --- Inicializar logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Leer datos del sheet ---
def get_active_fights():
    sheet = CLIENT.open(SPREADSHEET_NAME).sheet1
    data = sheet.get_all_records()
    upcoming = []
    now = datetime.now(CDMX_TZ)

    for row in data:
        if row["Estatus"].strip().lower() != "activa":
            continue
        try:
            fight_time = datetime.strptime(f"{row['Fecha']} {row['Hora (CDMX)']}", "%Y-%m-%d %H:%M")
            fight_time = CDMX_TZ.localize(fight_time)
            if fight_time > now:
                upcoming.append({
                    "datetime": fight_time,
                    "pelea": row["Pelea"],
                    "monto": row["Monto Apostado (MXN)"],
                    "cuota": row["Cuota"]
                })
        except Exception as e:
            logger.warning(f"Error en fila: {row} -> {e}")
    return upcoming

# --- Enviar mensaje de alerta ---
def send_alert(bot, fight):
    mensaje = f"""
⏰ *Alerta de apuesta!*
{fight['pelea']} inicia pronto.
Cantidad: {fight['monto']} - Cuota: {fight['cuota']}
Hora de inicio: {fight['datetime'].strftime('%H:%M')}
⚠️ ¡Verifica en Betsson! Posible cash out disponible en los próximos 5 minutos.
"""
    bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode='Markdown')

# --- Comandos Telegram ---
def start(update, context):
    update.message.reply_text("🤖 Bot de apuestas activado. Te avisaré antes de cada pelea.")

def status(update, context):
    peleas = get_active_fights()
    if not peleas:
        update.message.reply_text("No hay peleas activas registradas.")
        return
    texto = "📆 *Próximas peleas registradas:*\n"
    for f in peleas:
        texto += f"- {f['pelea']} a las {f['datetime'].strftime('%H:%M')} (CDMX)\n"
    update.message.reply_text(texto, parse_mode='Markdown')

def next_fight(update, context):
    peleas = sorted(get_active_fights(), key=lambda x: x['datetime'])
    if peleas:
        f = peleas[0]
        texto = f"""
📢 *Siguiente pelea:*
{f['pelea']}
Cantidad: {f['monto']} - Cuota: {f['cuota']}
Hora de inicio: {f['datetime'].strftime('%H:%M')} (CDMX)
"""
        update.message.reply_text(texto, parse_mode='Markdown')
    else:
        update.message.reply_text("No hay peleas activas registradas.")

# --- Loop de notificaciones ---
def notificacion_loop(bot):
    pendientes = {}
    while True:
        try:
            peleas = get_active_fights()
            now = datetime.now(CDMX_TZ)
            for f in peleas:
                t = f["datetime"]
                clave = f"{f['pelea']}|{t.strftime('%Y-%m-%d %H:%M')}"
                if clave not in pendientes:
                    pendientes[clave] = set()

                for delta in [120, 30, 10]:
                    alerta = t - timedelta(minutes=delta)
                    if alerta <= now and delta not in pendientes[clave]:
                        send_alert(bot, f)
                        pendientes[clave].add(delta)
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error en loop: {e}")
            time.sleep(60)

# --- Main ---
def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("next", next_fight))
    updater.start_polling()

    # Iniciar loop en segundo plano
    import threading
    thread = threading.Thread(target=notificacion_loop, args=(bot,))
    thread.start()

    updater.idle()

if __name__ == '__main__':
    main()