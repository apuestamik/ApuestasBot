import logging
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- Configuración ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SHEET_URL = os.getenv('SHEET_URL')
SHEET_CREDS = json.loads(os.getenv('SHEET_CREDS'))

# --- Logger ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Conexión a Google Sheets ---
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SHEET_CREDS, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
    return sheet

# --- Comandos ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text("¡Hola! Soy tu bot de apuestas 🎯\nUsa /help para ver los comandos.")

def help_command(update: Update, context: CallbackContext):
    help_text = (
        "/start - Inicia el bot\n"
        "/help - Muestra este mensaje de ayuda\n"
        "/status - Ver el estado actual de las apuestas\n"
        "/next - Ver la próxima apuesta programada"
    )
    update.message.reply_text(help_text)

def status(update: Update, context: CallbackContext):
    try:
        sheet = get_sheet()
        data = sheet.get_all_values()
        if data:
            response = "📊 *Estado actual de apuestas:*\n"
            for row in data[1:]:
                response += f"{row[0]} - {row[1]} - {row[2]}\n"
            update.message.reply_text(response, parse_mode="Markdown")
        else:
            update.message.reply_text("La hoja está vacía.")
    except Exception as e:
        logger.error(f"Error en /status: {e}")
        update.message.reply_text("⚠️ No pude obtener el estado.")

def next_bet(update: Update, context: CallbackContext):
    try:
        sheet = get_sheet()
        data = sheet.get_all_values()
        if len(data) > 1:
            next_row = data[1]
            response = f"🎯 Próxima apuesta:\nPartido: {next_row[0]}\nCantidad: {next_row[1]}\nHora: {next_row[2]}"
            update.message.reply_text(response)
        else:
            update.message.reply_text("No hay próximas apuestas.")
    except Exception as e:
        logger.error(f"Error en /next: {e}")
        update.message.reply_text("⚠️ No pude obtener la próxima apuesta.")

# --- Notificaciones automáticas ---
def send_notification(message: str):
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"Error enviando notificación: {e}")

# --- MAIN ---
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Comandos
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("next", next_bet))

    # Inicia el bot
    updater.start_polling()
    logger.info("Bot iniciado 🚀")
    updater.idle()

if __name__ == '__main__':
    main()