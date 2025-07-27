import os
from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply_text('Bot działa!')

def main():
    token = os.getenv('BOT_TOKEN')
    
    # Nowa składnia dla wersji 20+
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    
    # Używamy polling
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
