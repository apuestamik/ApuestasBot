import os
import json
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Cargar variables de entorno
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SHEET_URL = os.environ.get("SHEET_URL")
CREDENTIALS = json.loads(os.environ.get("GOOGLE_SHEETS_CREDENTIALS"))

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS, scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(SHEET_URL).sheet1

# /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "👋 ¡Hola! Soy tu bot de apuestas. Usa /help para ver mis comandos.")

# /help
@bot.message_handler(commands=["help"])
def help(message):
    bot.reply_to(message, "📋 Comandos disponibles:\n/start - Iniciar bot\n/status - Ver banca y apuestas\n/next - Próxima pelea")

# /status
@bot.message_handler(commands=["status"])
def status(message):
    rows = sheet.get_all_records()
    banca_total = sum([row["Apuesta"] for row in rows])
    bot.reply_to(message, f"💰 Banca actual: ${banca_total}\nApuestas activas: {len(rows)}")

# /next
@bot.message_handler(commands=["next"])
def next_fight(message):
    rows = sheet.get_all_records()
    for row in rows:
        if row["Resultado"] == "Pendiente":
            response = (
                f"📅 Próxima pelea: {row['Pelea']}\n"
                f"📆 Fecha: {row['Fecha']}\n"
                f"💵 Momio 1: {row['Momio 1']} | Momio 2: {row['Momio 2']}\n"
                f"💸 Apuesta: ${row['Apuesta']}"
            )
            bot.reply_to(message, response)
            return
    bot.reply_to(message, "🎉 No hay apuestas pendientes.")

print("✅ Bot está corriendo...")
bot.polling()