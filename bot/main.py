import os
import json
import logging
import gspread
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
SHEET_URL = os.environ.get('SHEET_URL')
SHEET_CREDS = json.loads(os.environ.get('SHEET_CREDS'))

# --- GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(SHEET_CREDS, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1  # Usa la primera hoja

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- COMANDOS ---
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('¡Hola! Soy tu bot de apuestas 📊\nUsa /help para ver mis comandos.')

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "/start - Iniciar el bot\n"
        "/help - Mostrar ayuda\n"
        "/status - Ver el estado actual de las apuestas\n"
        "/next - Ver la próxima apuesta programada"
    )

def status(update: Update, context: CallbackContext) -> None:
    try:
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            update.message.reply_text("No hay apuestas registradas en la hoja.")
            return

        msg = "📋 *Apuestas actuales:*\n"
        for row in data[1:]:  # Ignora encabezados
            msg += f"\n🎯 Partido: {row[0]}\n💰 Monto: {row[1]}\n📅 Fecha: {row[2]}\n"
        update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en /status: {e}")
        update.message.reply_text("⚠️ Ocurrió un error al obtener el estado.")

def next_bet(update: Update, context: CallbackContext) -> None:
    try:
        data = sheet.get_all_values()
        if len(data) < 2:
            update.message.reply_text("No hay próximas apuestas programadas.")
            return
        next_row = data[1]  # La primera apuesta después del encabezado
        msg = (
            f"🔮 *Próxima apuesta:*\n\n"
            f"🎯 Partido: {next_row[0]}\n"
            f"💰 Monto: {next_row[1]}\n"
            f"📅 Fecha: {next_row[2]}"
        )
        update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en /next: {e}")
        update.message.reply_text("⚠️ Ocurrió un error al obtener la próxima apuesta.")

# --- NOTIFICACIONES AUTOMÁTICAS ---
def send_notification(bot: Bot, message: str) -> None:
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