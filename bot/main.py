import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 ¡Hola! Soy tu bot de apuestas. Envíame /help para ver mis comandos."
    )

# Comando /help
def help_command(update: Update, context: CallbackContext):
    texto = (
        "📋 *Comandos disponibles:*\n"
        "/start - Mensaje de bienvenida\n"
        "/help - Esta ayuda\n"
        "/status - Estado de tu banca y apuestas\n"
        "/next - Próxima alerta programada\n"
    )
    update.message.reply_text(texto, parse_mode="Markdown")

# Comando /status (ejemplo de respuesta estática)
def status(update: Update, context: CallbackContext):
    # Aquí podrías leer tu Google Sheet para sacar datos reales
    update.message.reply_text(
        "💰 Estado de banca:\n"
        "- Banca actual: $2,000 MXN\n"
        "- Apuestas abiertas: 0\n"
    )

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("No encontré la variable TELEGRAM_TOKEN")

    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("status", status))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()