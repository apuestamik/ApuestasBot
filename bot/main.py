import os
import telegram
from telegram.ext import Updater, CommandHandler

# ENV Vars
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

def start(update, context):
    update.message.reply_text('👋 Hola! Bot listo para comandos.')

def next(update, context):
    update.message.reply_text('🎯 Próxima apuesta: Okolie vs Lerena, 1,500 MXN, cuota 1.45, 22:18')

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()