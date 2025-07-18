import os
import logging
import telegram
from telegram.ext import Updater, CommandHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import threading
import time

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ENV Vars
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_SHEETS_KEY = os.environ.get('GOOGLE_SHEETS_KEY')
CHAT_ID = os.environ.get('CHAT_ID')

# Telegram Bot
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEETS_KEY).sheet1

def clean_amount(amount_str):
    return ''.join(c for c in amount_str if c.isdigit() or c == '.')

def get_next_bet():
    try:
        data = sheet.get_all_values()
        if len(data) > 1:
            row = data[1]  # Solo la primera apuesta
            return {
                "partido": row[0],
                "cantidad": clean_amount(row[1]),
                "cuota": row[2],
                "hora": row[3]
            }
        else:
            return None
    except Exception as e:
        logger.error(f"Error leyendo Google Sheet: {e}")
        return None

def send_alert(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")

def monitor_bets():
    while True:
        next_bet = get_next_bet()
        if next_bet:
            try:
                now = datetime.now()
                hora_apuesta = datetime.strptime(next_bet['hora'], "%H:%M").replace(year=now.year, month=now.month, day=now.day)

                # Ajustar si la hora ya pasó hoy
                if hora_apuesta < now:
                    hora_apuesta += timedelta(days=1)

                # Notificaciones programadas
                alert_times = [
                    (hora_apuesta - timedelta(hours=2), "⏰ *Faltan 2 HORAS para la apuesta*\n🎯 Partido: {}\n💵 Cantidad: ${}\n📈 Cuota: {}\n⏰ Hora: {}".format(next_bet['partido'], next_bet['cantidad'], next_bet['cuota'], next_bet['hora'])),
                    (hora_apuesta - timedelta(hours=1), "⏰ *Falta 1 HORA para la apuesta*\n🎯 Partido: {}\n💵 Cantidad: ${}\n📈 Cuota: {}\n⏰ Hora: {}".format(next_bet['partido'], next_bet['cantidad'], next_bet['cuota'], next_bet['hora'])),
                    (hora_apuesta - timedelta(minutes=30), "⏰ *Faltan 30 MINUTOS para la apuesta*\n🎯 Partido: {}\n💵 Cantidad: ${}\n📈 Cuota: {}\n⏰ Hora: {}".format(next_bet['partido'], next_bet['cantidad'], next_bet['cuota'], next_bet['hora'])),
                    (hora_apuesta, "🚨 *ES HORA DEL CASH OUT*\n🎯 Partido: {}\n💵 Cantidad: ${}\n📈 Cuota: {}\n⏰ Hora: {}".format(next_bet['partido'], next_bet['cantidad'], next_bet['cuota'], next_bet['hora']))
                ]

                for alert_time, message in alert_times:
                    time_to_wait = (alert_time - datetime.now()).total_seconds()
                    if time_to_wait > 0:
                        time.sleep(time_to_wait)
                        send_alert(message)
            except Exception as e:
                logger.error(f"Error en monitor_bets: {e}")
        time.sleep(60)

def start(update, context):
    update.message.reply_text('👋 ¡Hola! Soy tu bot de apuestas. Usa /next para ver la próxima apuesta.')

def next(update, context):
    next_bet = get_next_bet()
    if next_bet:
        message = f"🎯 Próxima apuesta:\n" \
                  f"Partido: {next_bet['partido']}\n" \
                  f"Cantidad: ${next_bet['cantidad']}\n" \
                  f"Cuota: {next_bet['cuota']}\n" \
                  f"Hora: {next_bet['hora']}"
        update.message.reply_text(message)
    else:
        update.message.reply_text("No hay apuestas programadas.")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next))

    # Hilo para monitoreo
    threading.Thread(target=monitor_bets, daemon=True).start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()