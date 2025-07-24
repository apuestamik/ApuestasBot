import os
import logging
import pytz
import time
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot, ParseMode, Update
from telegram.ext import CommandHandler, Updater, CallbackContext
from telegram.error import TelegramError

# ==========================
# CONFIGURACIÓN
# ==========================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # Ejemplo: '8154311331'
GOOGLE_SHEET_NAME = "Apuestas Telegram"

# Zona horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# Inicializar bot
bot = Bot(token=TELEGRAM_TOKEN)

# ==========================
# ACCESO A GOOGLE SHEETS
# ==========================
def get_sheet_data():
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        data = sheet.get_all_records()
        return data
    except Exception as e:
        logging.error(f"Error al acceder a Google Sheets: {e}")
        return []

# ==========================
# ALERTAS DE APOSTAS
# ==========================
def enviar_alerta(pelea, tiempo_restante):
    mensaje = f"📢 *Alerta de pelea próxima*\n\n🥊 *{pelea['Pelea']}*\n💰 Monto: ${pelea['Monto Apostado (MXN)']} MXN\n📈 Cuota: {pelea['Cuota']}\n\n⏰ *Faltan {tiempo_restante} para el inicio.*\n\n⚠️ ¡Verifica en *Betsson*! Posible *cash out* disponible en los próximos 5 minutos."
    try:
        bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode=ParseMode.MARKDOWN)
    except TelegramError as e:
        logging.error(f"Error enviando mensaje: {e}")

def verificar_alertas():
    now_utc = datetime.now(pytz.utc)
    sheet_data = get_sheet_data()
    for pelea in sheet_data:
        if pelea['Estatus'].strip().lower() != 'activa':
            continue
        try:
            hora_cdmx = datetime.strptime(f"{pelea['Fecha']} {pelea['Hora (CDMX)']}", "%Y-%m-%d %H:%M")
            hora_cdmx = CDMX_TZ.localize(hora_cdmx)
            hora_utc = hora_cdmx.astimezone(pytz.utc)
            delta = hora_utc - now_utc

            minutos_restantes = int(delta.total_seconds() / 60)

            if minutos_restantes in [120, 30, 10]:  # 2h, 30min, 10min
                tiempo_texto = {
                    120: "2 horas",
                    30: "30 minutos",
                    10: "10 minutos"
                }
                enviar_alerta(pelea, tiempo_texto[minutos_restantes])
        except Exception as e:
            logging.error(f"Error en el procesamiento de pelea: {pelea}. Error: {e}")

# ==========================
# COMANDOS TELEGRAM
# ==========================
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Bienvenido. Recibirás notificaciones automáticas de tus apuestas.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Comandos disponibles:\n/start\n/help\n/status\n/next")

def status(update: Update, context: CallbackContext):
    update.message.reply_text("✅ El bot está activo y funcionando correctamente.")

def next_command(update: Update, context: CallbackContext):
    data = get_sheet_data()
    activas = [p for p in data if p['Estatus'].strip().lower() == 'activa']
    if not activas:
        update.message.reply_text("📭 No hay peleas activas registradas.")
        return

    mensaje = "📅 *Próximas peleas activas:*\n"
    for pelea in activas:
        mensaje += f"\n🥊 *{pelea['Pelea']}*\n📆 Fecha: {pelea['Fecha']}\n⏰ Hora CDMX: {pelea['Hora (CDMX)']}\n💰 ${pelea['Monto Apostado (MXN)']} a cuota {pelea['Cuota']}\n"
    update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

# ==========================
# LOOP PRINCIPAL
# ==========================
def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # Comandos Telegram
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("next", next_command))

    updater.start_polling()

    print("✅ Bot iniciado y escuchando alertas...")

    # Bucle de verificación cada minuto
    while True:
        try:
            verificar_alertas()
        except Exception as e:
            logging.error(f"Error en el loop de alertas: {e}")
        time.sleep(60)

if __name__ == '__main__':
    main()