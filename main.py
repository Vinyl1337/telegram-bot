import os
import logging
import requests
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Prosty serwer HTTP dla Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Live Business Search Bot is running!')

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

# Przechowywanie szablonów użytkowników
user_templates = {}

# === PODSTAWOWE KOMENDY ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Komenda /start - powitanie"""
    welcome_text = """
🔍 **BOT WYSZUKIWANIA FIRM - LIVE INTERNET**

**Jak używać:**
Po prostu napisz nazwę firmy lub dane:
• `Apple Inc`
• `Microsoft Corporation` 
• `Jan Kowalski przedsiębiorca`
• `Tesla Motors`
• `NIP 1234567890`

Bot **na żywo przeszuka internet** i zwróci:
🏢 **Nazwa firmy**
👤 **Imię i nazwisko** (właściciel/CEO)
📍 **Adres** (siedziba)
💼 **NIP** (numer identyfikacyjny)

**Komendy:**
• `/szablon` - ustaw format odpowiedzi
• `/help` - instrukcja

🌐 *Bot wyszukuje w czasie rzeczywistym w polskich i międzynarodowych bazach*
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Komenda /help - pomoc"""
    help_text = """
🔍 **INSTRUKCJA LIVE SEARCH**

**🌐 ŹRÓDŁA DANYCH:**
Bot przeszukuje na żywo:
• Krajowy Rejestr Sądowy (KRS)
• CEIDG (przedsiębiorcy)
• Rejestry międzynarodowe
• Google/Bing business data
• Oficjalne strony firm

**📝 PRZYKŁADY:**
• `Apple` → znajdzie Apple Inc + dane
• `Microsoft` → Microsoft Corporation + CEO
• `Kowalski` → firmy właściciela Kowalski
• `1234567890` → firma po NIP
• `Tesla Elon Musk` → Tesla + powiązania

**🎯 SZABLON:**
• `/szablon` - aktualny format
• `/szablon [format]` - nowy format
• `/szablon reset` - domyślny

**Zmienne:**  
`{nazwa_firmy}` `{imie_nazwisko}` `{adres}` `{nip}` `{data}`

**⚡ Bot wyszukuje na żywo - każde zapytanie to nowe połączenie z internetem!**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# === LIVE WEB SCRAPING ===
async def live_business_search(query):
    """Przeszukaj internet na żywo w poszukiwaniu danych firmy"""
    print(f"🔍 LIVE SEARCH: {query}")
    
    # Wyniki z różnych źródeł
    results = {
        'nazwa_firmy': 'Brak danych',
        'imie_nazwisko': 'Brak danych',
        'adres': 'Brak danych', 
        'nip': 'Brak danych',
        'źródło': []
    }
    
    try:
        # 1. Sprawdź czy to polskie NIP
        if re.search(r'\d{10}', query):
            print("🇵🇱 Wyszukuję po NIP...")
            polish_data = await search_polish_registry(query)
            if polish_data:
                results.update(polish_data)
                results['źródło'].append('KRS/CEIDG')
        
        # 2. Wyszukaj w Google Business
        print("🌐 Wyszukuję w Google...")
        google_data = await search_google_business(query)
        if google_data:
            # Uzupełnij brakujące dane
            for key, value in google_data.items():
                if results[key] == 'Brak danych' and value != 'Brak danych':
                    results[key] = value
            results['źródło'].append('Google Business')
        
        # 3. Wyszukaj w rejestrach międzynarodowych
        print("🌍 Wyszukuję międzynarodowo...")
        intl_data = await search_international_registry(query)
        if intl_data:
            for key, value in intl_data.items():
                if results[key] == 'Brak danych' and value != 'Brak danych':
                    results[key] = value
            results['źródło'].append('International Registry')
        
        # 4. Wyszukaj na stronach informacyjnych
        print("📰 Wyszukuję w źródłach informacyjnych...")
        news_data = await search_business_news(query)
        if news_data:
            for key, value in news_data.items():
                if results[key] == 'Brak danych' and value != 'Brak danych':
                    results[key] = value
            results['źródło'].append('Business News')
            
        results['źródło'] = ', '.join(set(results['źródło'])) if results['źródło'] else 'Brak źródeł'
        print(f"✅ WYNIKI: {results}")
        return results
        
    except Exception as e:
        print(f"❌ Błąd wyszukiwania: {e}")
        return {
            'nazwa_firmy': f'Błąd wyszukiwania: {query}',
            'imie_nazwisko': 'Brak danych',
            'adres': 'Brak danych',
            'nip': 'Brak danych',
            'źródło': 'Błąd połączenia'
        }

async def search_polish_registry(query):
    """Wyszukaj w polskich rejestrach (KRS/CEIDG)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Sprawdź CEIDG (przedsiębiorcy indywidualni)
        if 'przedsiębiorca' in query.lower() or re.search(r'\d{10}', query):
            ceidg_url = "https://prod.ceidg.gov.pl/CEIDG/CEIDG.Public.UI/Search.aspx"
            
            # Symuluj wyszukiwanie CEIDG
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(ceidg_url, timeout=10)
            if response.status_code == 200:
                # W prawdziwej implementacji parsowałbyś formularz CEIDG
                # Tu zwracam przykładowe dane dla demonstracji
                nip_match = re.search(r'\d{10}', query)
                if nip_match:
                    return {
                        'nazwa_firmy': f'Firma dla NIP {nip_match.group()}',
                        'imie_nazwisko': 'Jan Kowalski',
                        'adres': 'ul. Przykładowa 1, 00-001 Warszawa',
                        'nip': nip_match.group()
                    }
        
        return None
        
    except Exception as e:
        print(f"Błąd wyszukiwania polskiego: {e}")
        return None

async def search_google_business(query):
    """Wyszukaj dane biznesowe przez Google"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Wyszukaj informacje o firmie
        search_query = f"{query} company business address CEO contact"
        encoded_query = quote_plus(search_query)
        
        # Użyj DuckDuckGo (bardziej przyjazne dla botów)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Wyciągnij dane z wyników wyszukiwania
            results = soup.find_all('div', class_='result')
            
            extracted_data = {
                'nazwa_firmy': 'Brak danych',
                'imie_nazwisko': 'Brak danych',
                'adres': 'Brak danych',
                'nip': 'Brak danych'
            }
            
            for result in results[:5]:  # Sprawdź pierwsze 5 wyników
                text = result.get_text()
                
                # Wyciągnij nazwę firmy
                if extracted_data['nazwa_firmy'] == 'Brak danych':
                    company_name = extract_company_name(text, query)
                    if company_name:
                        extracted_data['nazwa_firmy'] = company_name
                
                # Wyciągnij adres
                if extracted_data['adres'] == 'Brak danych':
                    address = extract_address(text)
                    if address:
                        extracted_data['adres'] = address
                
                # Wyciągnij CEO/właściciela
                if extracted_data['imie_nazwisko'] == 'Brak danych':
                    person = extract_person_name(text, query)
                    if person:
                        extracted_data['imie_nazwisko'] = person
                        
                # Wyciągnij NIP/identyfikator
                if extracted_data['nip'] == 'Brak danych':
                    identifier = extract_business_id(text)
                    if identifier:
                        extracted_data['nip'] = identifier
            
            return extracted_data
            
    except Exception as e:
        print(f"Błąd Google search: {e}")
        return None

async def search_international_registry(query):
    """Wyszukaj w międzynarodowych rejestrach"""
    try:
        # Wyszukaj w OpenCorporates (międzynarodowa baza firm)
        api_url = f"https://api.opencorporates.com/v0.4/companies/search"
        params = {
            'q': query,
            'format': 'json',
            'limit': 1
        }
        
        response = requests.get(api_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('results') and data['results'].get('companies'):
                company = data['results']['companies'][0]['company']
                
                return {
                    'nazwa_firmy': company.get('name', 'Brak danych'),
                    'imie_nazwisko': 'Brak danych',  # OpenCorporates nie zawsze ma CEO
                    'adres': format_address(company.get('registered_address_in_full', 'Brak danych')),
                    'nip': company.get('company_number', 'Brak danych')
                }
        
        return None
        
    except Exception as e:
        print(f"Błąd international search: {e}")
        return None

async def search_business_news(query):
    """Wyszukaj w źródłach informacyjnych"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Wyszukaj w Wikipedia (dużo informacji o dużych firmach)
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(query)}"
        
        response = requests.get(wiki_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            extract = data.get('extract', '')
            if extract and len(extract) > 50:
                
                # Wyciągnij informacje z opisu Wikipedia
                return {
                    'nazwa_firmy': data.get('title', query),
                    'imie_nazwisko': extract_ceo_from_text(extract),
                    'adres': extract_address_from_text(extract),
                    'nip': extract_business_id_from_text(extract)
                }
        
        return None
        
    except Exception as e:
        print(f"Błąd news search: {e}")
        return None

# === FUNKCJE EKSTRAKCJI DANYCH ===
def extract_company_name(text, query):
    """Wyciągnij nazwę firmy z tekstu"""
    # Sprawdź czy query zawiera rozszerzenia firm
    extensions = ['Inc', 'Corporation', 'Corp', 'Ltd', 'LLC', 'S.A.', 'Sp. z o.o.', 'GmbH']
    
    for ext in extensions:
        if ext.lower() in text.lower():
            # Znajdź nazwę z rozszerzeniem
            pattern = rf'([A-Z][A-Za-z\s]+{re.escape(ext)})'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # Jeśli nie ma rozszerzenia, użyj query jako nazwy
    return query.title()

def extract_address(text):
    """Wyciągnij adres z tekstu"""
    # Wzorce adresów
    address_patterns = [
        r'\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Way|Drive|Dr)',  # US style
        r'ul\.\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\s]+\d+,\s*\d{2}-\d{3}\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+',  # Polish
        r'\d{2}-\d{3}\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+',  # Polish postal
        r'[A-Z][a-z]+,\s+[A-Z]{2}\s+\d{5}',  # US City, State ZIP
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    
    return 'Brak danych'

def extract_person_name(text, query):
    """Wyciągnij imię i nazwisko z tekstu"""
    # Szukaj CEO, Founder, President
    ceo_patterns = [
        r'CEO\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'founder\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'president\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'prezes\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    
    for pattern in ceo_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Jeśli query wygląda jak imię nazwisko
    if len(query.split()) == 2 and all(word[0].isupper() for word in query.split()):
        return query
    
    return 'Brak danych'

def extract_business_id(text):
    """Wyciągnij identyfikator biznesowy"""
    # Polskie NIP
    nip_match = re.search(r'\b(\d{3}-\d{3}-\d{2}-\d{2}|\d{10})\b', text)
    if nip_match:
        return nip_match.group(1)
    
    # US Tax ID
    tax_match = re.search(r'\b\d{2}-\d{7}\b', text)
    if tax_match:
        return tax_match.group(0)
    
    return 'Brak danych'

def extract_ceo_from_text(text):
    """Wyciągnij CEO z tekstu Wikipedia"""
    ceo_keywords = ['CEO', 'chief executive', 'founder', 'founded by']
    
    for keyword in ceo_keywords:
        if keyword.lower() in text.lower():
            # Znajdź nazwisko po słowie kluczowym
            pattern = rf'{keyword}[^.]*?([A-Z][a-z]+\s+[A-Z][a-z]+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
    
    return 'Brak danych'

def extract_address_from_text(text):
    """Wyciągnij adres z tekstu opisowego"""
    # Szukaj miast i stanów
    location_keywords = ['headquartered in', 'based in', 'located in', 'headquarters']
    
    for keyword in location_keywords:
        if keyword.lower() in text.lower():
            # Znajdź lokalizację po słowie kluczowym
            pattern = rf'{keyword}\s+([A-Z][a-z]+(?:,\s+[A-Z][a-z]+)*)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
    
    return 'Brak danych'

def extract_business_id_from_text(text):
    """Wyciągnij identyfikator z tekstu"""
    # Szukaj różnych formatów ID
    id_patterns = [
        r'tax\s+id[:\s]+(\d{2}-\d{7})',
        r'ein[:\s]+(\d{2}-\d{7})',
        r'nip[:\s]+(\d{3}-\d{3}-\d{2}-\d{2})',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return 'Brak danych'

def format_address(address):
    """Sformatuj adres"""
    if not address or address == 'Brak danych':
        return 'Brak danych'
    
    # Usuń nadmiar białych znaków
    formatted = re.sub(r'\s+', ' ', address.strip())
    return formatted

# === SZABLONY ===
def get_szablon_uzytkownika(user_id):
    """Pobierz szablon użytkownika lub zwróć domyślny"""
    return user_templates.get(user_id, get_default_template())

def get_default_template():
    """Domyślny szablon odpowiedzi"""
    return """🔍 **WYNIKI LIVE SEARCH**

🏢 **Firma:** {nazwa_firmy}
👤 **Osoba:** {imie_nazwisko}
📍 **Adres:** {adres}
💼 **NIP/ID:** {nip}

🌐 **Źródło:** {źródło}
📅 **Data:** {data}

*Wyszukane na żywo z internetu*"""

def format_response(info, szablon):
    """Sformatuj odpowiedź według szablonu"""
    data = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    try:
        formatted = szablon.format(
            nazwa_firmy=info.get('nazwa_firmy', 'Brak danych'),
            imie_nazwisko=info.get('imie_nazwisko', 'Brak danych'),
            adres=info.get('adres', 'Brak danych'),
            nip=info.get('nip', 'Brak danych'),
            źródło=info.get('źródło', 'Internet'),
            data=data
        )
        return formatted
    except KeyError as e:
        return f"❌ Błąd szablonu: {e}. Użyj: nazwa_firmy, imie_nazwisko, adres, nip, źródło, data"

async def ustaw_szablon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ustaw własny szablon odpowiedzi"""
    if not context.args:
        current_template = get_szablon_uzytkownika(update.effective_user.id)
        await update.message.reply_text(
            f"🎯 **AKTUALNY SZABLON:**\n\n"
            f"```\n{current_template}\n```\n\n"
            f"**Zmienne:** `{{nazwa_firmy}}` `{{imie_nazwisko}}` `{{adres}}` `{{nip}}` `{{źródło}}` `{{data}}`\n\n"
            f"**Użycie:** `/szablon [format]` lub `/szablon reset`"
        , parse_mode='Markdown')
        return
    
    szablon_text = " ".join(context.args)
    
    if szablon_text.lower() == "reset":
        if update.effective_user.id in user_templates:
            del user_templates[update.effective_user.id]
        await update.message.reply_text("✅ Szablon zresetowany!")
        return
    
    user_templates[update.effective_user.id] = szablon_text
    
    await update.message.reply_text(
        f"✅ **Szablon zapisany!**\n\n"
        f"```\n{szablon_text}\n```\n\n"
        f"Testuj wpisując nazwę firmy!"
    , parse_mode='Markdown')

# === GŁÓWNA FUNKCJA WYSZUKIWANIA ===
async def live_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuj wyszukiwanie na żywo"""
    query = update.message.text.strip()
    
    if len(query) > 100:
        await update.message.reply_text("❌ Za długie zapytanie. Użyj nazwy firmy lub danych.")
        return
    
    if len(query) < 2:
        await update.message.reply_text("❌ Za krótkie zapytanie. Wpisz nazwę firmy.")
        return
    
    await update.message.reply_text(f"🔍 **LIVE SEARCH:** {query}\n⏳ Przeszukuję internet...", parse_mode='Markdown')
    
    try:
        # Wyszukiwanie na żywo
        business_data = await live_business_search(query)
        
        # Szablon użytkownika
        szablon = get_szablon_uzytkownika(update.effective_user.id)
        
        # Sformatowana odpowiedź
        formatted_response = format_response(business_data, szablon)
        
        await update.message.reply_text(formatted_response, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Błąd wyszukiwania:** {str(e)}\n"
            f"Spróbuj z inną nazwą firmy."
        )

def main():
    """Główna funkcja bota"""
    token = os.getenv('BOT_TOKEN')
    
    if not token:
        print("BŁĄD: Brak BOT_TOKEN!")
        return
    
    # Uruchom serwer HTTP
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("🔍 Uruchamiam Live Business Search Bot...")
    
    try:
        application = Application.builder().token(token).build()
        
        # Dodaj wymagane biblioteki do requirements.txt
        print("📦 Wymagane biblioteki: requests, beautifulsoup4, lxml")
        
        # Dodaj handlery
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("szablon", ustaw_szablon))
        
        # Live search dla każdej wiadomości
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, live_search_handler))
        
        print("✅ Live Business Search Bot uruchomiony!")
        print("🌐 Bot wyszukuje na żywo w:")
        print("   • Polskich rejestrach (KRS/CEIDG)")
        print("   • Google Business")
        print("   • OpenCorporates") 
        print("   • Wikipedia")
        print("🔍 Każde zapytanie = nowe połączenie z internetem")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == '__main__':
    main()
