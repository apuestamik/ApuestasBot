import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import threading
import time

# Configuración de Google Sheets
SCOPE = ['https://spreadsheets.google.com/feeds']
CREDS_JSON = os.getenv('SHEET_CREDS')
SHEET_URL = os.getenv('SHEET_URL')

# Función para verificar próximas apuestas
def check_alerts(context: CallbackContext):
    gc = gspread.service_account_from_dict(eval(CREDS_JSON))
    sheet = gc.open_by_url(SHEET_URL).sheet1
    rows = sheet.get_all_records()
    now = datetime.now()
    for row in rows:
        if row['Estado']=='Activa' and row['Hora CDMX']:
            fight_time = datetime.strptime(row['Hora CDMX'], '%H:%M').replace(
                year=now.year, month=now.month, day=row['Fecha'].day)  # Ajusta fecha
            delta = fight_time - now
            chat_id = int(os.getenv('TELEGRAM_CHAT_ID'))
            if 0 < delta.total_seconds() < 7200:  # 2 hrs
                context.bot.send_message(chat_id=chat_id, text=f"‼️ Próxima pelea: {row['Pelea']} a las {row['Hora CDMX']} CDMX (2 h).")
            if 0 < delta.total_seconds() < 1800:
                context.bot.send_message(chat_id=chat_id, text=f"⚠️ Próxima pelea {row['Pelea']} en 30 min.")
            if 0 < delta.total_seconds() < 600:
                context.bot.send_message(chat_id=chat_id, text=f"🎯 Ataque final: {row['Pelea']} dentro de 10 min. Hora: {row['Hora CDMX']} CDMX")

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Bot activo. Tendrás alertas de próximas apuestas.")

def main():
    token = os.getenv('TELEGRAM_TOKEN')
    updater = Updater(token=token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))

    job_queue = updater.job_queue
    job_queue.run_repeating(check_alerts, interval=60, first=10)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()