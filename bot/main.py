import logging
import os
import pytz
import gspread
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update

# Configuración básica del logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Variables de entorno
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME')

# Zona horaria de CDMX
CDMX_TZ = pytz.timezone("America/Mexico_City")

# Autenticación con Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = eval(os.getenv('SHEET_CREDS'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)
apuestas_sheet = sheet.worksheet(SHEET_NAME)
checklist_sheet = sheet.worksheet("Checklist")

# Función para obtener apuestas activas
def get_apuestas_activas():
    records = apuestas_sheet.get_all_records()
    activas = []
    for row in records:
        if row.get("Estatus", "").strip().lower() == "activa":
            activas.append(row)
    return activas

# Comandos de bot
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Bot de apuestas activo. Usa /next para ver la siguiente pelea.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("/start - Iniciar bot\n/next - Ver siguiente pelea\n/status - Ver estado del sistema\n/help - Ayuda")

def status(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Sistema funcionando correctamente y monitoreando peleas activas.")

def next_fight(update: Update, context: CallbackContext):
    activas = get_apuestas_activas()
    if not activas:
        update.message.reply_text("⛔ No hay peleas activas registradas.")
        return

    activas.sort(key=lambda x: x['Fecha'] + ' ' + x['Hora (CDMX)'])
    pelea = activas[0]
    mensaje = f"📅 Próxima pelea: {pelea['Pelea']}\n🕒 Hora: {pelea['Hora (CDMX)']}\n💰 Monto: ${pelea['Monto Apostado (MXN)']}\n🔥 Cuota: {pelea['Cuota']}"
    update.message.reply_text(mensaje)

# Envío de alertas programadas
def enviar_alerta(context: CallbackContext):
    now_utc = datetime.now(pytz.utc)
    activas = get_apuestas_activas()
    for pelea in activas:
        try:
            pelea_dt_cdmx = datetime.strptime(f"{pelea['Fecha']} {pelea['Hora (CDMX)']}", "%d-%b-%Y %H:%M")
            pelea_dt_cdmx = CDMX_TZ.localize(pelea_dt_cdmx)
            pelea_dt_utc = pelea_dt_cdmx.astimezone(pytz.utc)
            delta = pelea_dt_utc - now_utc

            mensaje_alerta = f"⚠️ ¡Verifica en Betsson! Posible cash out disponible en los próximos 5 minutos.\n📍 {pelea['Pelea']} - {pelea['Hora (CDMX)']}"

            if timedelta(minutes=118) < delta <= timedelta(minutes=122):
                context.bot.send_message(chat_id=CHAT_ID, text="⏰ 2 HORAS PARA LA PELEA\n" + mensaje_alerta)
            elif timedelta(minutes=28) < delta <= timedelta(minutes=32):
                context.bot.send_message(chat_id=CHAT_ID, text="⏰ 30 MINUTOS PARA LA PELEA\n" + mensaje_alerta)
            elif timedelta(minutes=8) < delta <= timedelta(minutes=12):
                context.bot.send_message(chat_id=CHAT_ID, text="⏰ 10 MINUTOS PARA LA PELEA\n" + mensaje_alerta)
        except Exception as e:
            logging.error(f"Error procesando pelea: {pelea.get('Pelea', 'desconocida')} - {e}")

# Nueva función: agregar fila al checklist
def agregar_a_checklist(pelea_data: dict):
    fila = [
        pelea_data.get("Peleador A", ""),
        pelea_data.get("Peleador B", ""),
        pelea_data.get("Fecha", ""),
        pelea_data.get("Hora CDMX", ""),
        pelea_data.get("Estilo A", ""),
        pelea_data.get("Estilo B", ""),
        pelea_data.get("Campamento A", ""),
        pelea_data.get("Fallos Rival", ""),
        pelea_data.get("Estado Mental", ""),
        pelea_data.get("Ventaja Física", ""),
        pelea_data.get("Última Victoria", ""),
        pelea_data.get("Cuota", ""),
        pelea_data.get("Transmisión", ""),
        pelea_data.get("Revisión Cash Out", ""),
        pelea_data.get("Dominante", ""),
        pelea_data.get("¿Apuesta Sugerida?", "")
    ]
    checklist_sheet.append_row(fila, value_input_option="USER_ENTERED")

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("next", next_fight))

    job_queue = updater.job_queue
    job_queue.run_repeating(enviar_alerta, interval=60, first=10)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


# Nuevo comando para agregar pelea al checklist desde Telegram
def analizar(update: Update, context: CallbackContext):
    try:
        if len(context.args) < 16:
            update.message.reply_text("⚠️ Formato incompleto. Debes enviar 16 datos separados por '|'.\nEjemplo:\n/analizar Keyshawn Davis|Miguel Madueño|10-ago-2025|20:00|Técnico|Frontal|✅|✅|✅|✅|✅|1.28|DAZN|✅|Keyshawn Davis|✅")
            return

        pelea_data = {
            "Peleador A": context.args[0],
            "Peleador B": context.args[1],
            "Fecha": context.args[2],
            "Hora CDMX": context.args[3],
            "Estilo A": context.args[4],
            "Estilo B": context.args[5],
            "Campamento A": context.args[6],
            "Fallos Rival": context.args[7],
            "Estado Mental": context.args[8],
            "Ventaja Física": context.args[9],
            "Última Victoria": context.args[10],
            "Cuota": context.args[11],
            "Transmisión": context.args[12],
            "Revisión Cash Out": context.args[13],
            "Dominante": context.args[14],
            "¿Apuesta Sugerida?": context.args[15]
        }

        agregar_a_checklist(pelea_data)
        update.message.reply_text("✅ Análisis agregado exitosamente a la hoja 'Checklist'.")
    except Exception as e:
        logging.error(f"Error al agregar análisis: {e}")
        update.message.reply_text("❌ Error al agregar el análisis. Revisa el formato o intenta más tarde.")

# Agregar handler de /analizar
dispatcher.add_handler(CommandHandler("analizar", analizar, pass_args=True))