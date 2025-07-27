import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Prosty serwer HTTP dla Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"HTTP server running on port {port}")
    server.serve_forever()

# Włącz logowanie
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🤖 Bot działa poprawnie!')

def main():
    token = os.getenv('BOT_TOKEN')
    
    if not token:
        print("BŁĄD: Brak BOT_TOKEN!")
        return
    
    # Uruchom serwer HTTP w osobnym wątku
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("Uruchamiam bota...")
    
    try:
        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", start))
        
        print("Bot skonfigurowany, uruchamiam polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Błąd: {e}")

if __name__ == '__main__':
    main()
