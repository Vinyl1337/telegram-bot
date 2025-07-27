import os
from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply_text('Bot działa!')

def main():
    # Token z zmiennej środowiskowej (bezpieczniej)
    token = os.getenv('BOT_TOKEN')
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    
    # Dla Render używamy polling zamiast webhook
    app.run_polling()

if __name__ == '__main__':
    main()
