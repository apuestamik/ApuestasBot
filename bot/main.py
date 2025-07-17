import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "¡Hola! Soy tu bot de apuestas. Envíame /help para ver mis comandos."
    )

def main():
    # Recupera el token desde la variable de entorno
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("No encontré la variable TELEGRAM_TOKEN")

    # Inicializa el bot
    updater = Updater(token)
    dp = updater.dispatcher

    # Registro de comandos
    dp.add_handler(CommandHandler("start", start))

    # Arranca el polling
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()