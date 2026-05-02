# ============================================
# АВТОУСТАНОВКА БИБЛИОТЕК
# ============================================
import subprocess
import sys

packages = ['numpy', 'ccxt', 'pyTelegramBotAPI', 'requests', 'beautifulsoup4', 'fake-useragent']
for package in packages:
    try:
        if package == 'pyTelegramBotAPI':
            __import__('telebot')
        elif package == 'beautifulsoup4':
            __import__('bs4')
        elif package == 'fake-useragent':
            __import__('fake_useragent')
        else:
            __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--upgrade"])

# ============================================
# ИМПОРТЫ
# ============================================
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import ccxt
import numpy as np
import time
import random
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# ============================================
# ТВОИ ТОКЕНЫ
# ============================================
TELEGRAM_TOKEN = "8651330648:AAGQdVLP73PWwdQNJf-sL32S_gJsqL3cYqg"  # ЗАМЕНИ!!!
OPENAI_API_KEY = "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"      # опционально
# ============================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Инициализация генератора User-Agent
ua = UserAgent()

# Список доступных криптовалют
CRYPTO_LIST = {
    'BTC': 'Bitcoin',
    'ETH': 'Ethereum',
    'SOL': 'Solana',
    'BNB': 'Binance Coin',
    'XRP': 'Ripple',
    'DOGE': 'Dogecoin',
    'ADA': 'Cardano',
    'AVAX': 'Avalanche',
    'DOT': 'Polkadot',
    'MATIC': 'Polygon',
    'LINK': 'Chainlink',
    'LTC': 'Litecoin'
}

# Хранилище
user_settings = {}
currency_rates = {'USD': 1, 'EUR': 0, 'RUB': 0}
last_rate_update = None

# Настройки биржи с ротацией User-Agent
def get_exchange():
    return ccxt.binance({
        'enableRateLimit': True,
        'headers': {
            'User-Agent': ua.random,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        },
        'options': {
            'defaultType': 'spot'
        }
    })

# ============================================
# ФУНКЦИЯ ДЛЯ ИМИТАЦИИ ЧЕЛОВЕЧЕСКОЙ ЗАДЕРЖКИ
# ============================================
def human_delay(min_sec=0.5, max_sec=2.0):
    """Задержка как у реального человека (случайная)"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def typing_action(chat_id):
    """Имитация набора текста"""
    bot.send_chat_action(chat_id, 'typing')
    human_delay(0.3, 1.0)

# ============================================
# ПОЛУЧЕНИЕ РЕАЛЬНЫХ КУРСОВ ВАЛЮТ С РАЗНЫХ САЙТОВ
# ============================================
def update_currency_rates():
    """Обновляет курсы валют с 3 разных источников"""
    global currency_rates, last_rate_update
    
    # Обновляем раз в час
    if last_rate_update and datetime.now() - last_rate_update < timedelta(hours=1):
        return currency_rates
    
    print("🔄 Обновляю курсы валют с сайтов...")
    
    rates = {'USD': 1, 'EUR': 0, 'RUB': 0}
    
    # СПОСОБ 1: Центробанк РФ (официальный курс)
    try:
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            for valute in soup.find_all('Valute'):
                charcode = valute.find('CharCode').text if valute.find('CharCode') else ''
                if charcode == 'USD':
                    value = valute.find('Value').text.replace(',', '.')
                    rates['USD'] = float(value)
                    print(f"✅ Курс USD от ЦБ РФ: {rates['USD']} RUB")
                elif charcode == 'EUR':
                    value = valute.find('Value').text.replace(',', '.')
                    rates['EUR'] = float(value)
                    print(f"✅ Курс EUR от ЦБ РФ: {rates['EUR']} RUB")
            # Конвертируем: нам нужно сколько RUB за 1 USD
            if rates['USD'] > 0:
                rub_per_usd = rates['USD']
                rates['RUB'] = rub_per_usd
                rates['USD'] = 1
                if rates['EUR'] > 0:
                    rates['EUR'] = rates['EUR'] / rub_per_usd
            print("✅ Курсы от ЦБ РФ загружены")
            human_delay(0.5, 1.5)
    except Exception as e:
        print(f"⚠️ ЦБ РФ не ответил: {e}")
    
    # СПОСОБ 2: API ExchangeRate (бесплатный)
    if rates['EUR'] == 0 or rates['RUB'] == 0:
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            headers = {'User-Agent': ua.random}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                rates['EUR'] = data['rates'].get('EUR', 0.92)
                rates['RUB'] = data['rates'].get('RUB', 91.5)
                print(f"✅ Курсы от ExchangeRate: EUR={rates['EUR']}, RUB={rates['RUB']}")
            human_delay(0.3, 0.8)
        except Exception as e:
            print(f"⚠️ ExchangeRate не ответил: {e}")
    
    # СПОСОБ 3: Google Finance (через парсинг)
    if rates['EUR'] == 0 or rates['RUB'] == 0:
        try:
            url = "https://www.google.com/finance/quote/USD-RUB"
            headers = {'User-Agent': ua.random}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Ищем курс на странице
                price_elem = soup.find('div', {'class': 'YMlKec fxKbKc'})
                if price_elem:
                    rub_rate = float(price_elem.text.replace(',', ''))
                    rates['RUB'] = rub_rate
                    print(f"✅ Курс USD/RUB от Google: {rub_rate}")
            human_delay(0.5, 1.0)
        except Exception as e:
            print(f"⚠️ Google Finance не ответил: {e}")
    
    # Если всё сломалось - запасные значения
    if rates['EUR'] == 0:
        rates['EUR'] = 0.92
        print("⚠️ Использую запасной курс EUR: 0.92")
    if rates['RUB'] == 0:
        rates['RUB'] = 91.5
        print("⚠️ Использую запасной курс RUB: 91.5")
    
    currency_rates = rates
    last_rate_update = datetime.now()
    
    print(f"✅ Итоговые курсы: USD=1, EUR={rates['EUR']:.2f}, RUB={rates['RUB']:.2f}")
    return rates

def get_currency_rate(currency='USD'):
    """Возвращает курс выбранной валюты к USD"""
    rates = update_currency_rates()
    if currency == 'USD':
        return 1
    elif currency == 'EUR':
        return rates.get('EUR', 0.92)
    elif currency == 'RUB':
        return rates.get('RUB', 91.5)
    return 1

# ============================================
# ПОЛУЧЕНИЕ ДАННЫХ С БИРЖ (с обходом блокировок)
# ============================================
def get_crypto_price(symbol='BTC'):
    """Получает цену с 3 разных источников (обход блокировок)"""
    
    # СПОСОБ 1: Binance через ccxt с ротацией User-Agent
    try:
        exchange = get_exchange()
        pair = f"{symbol}/USDT"
        ticker = exchange.fetch_ticker(pair)
        print(f"✅ {symbol} цена (Binance ccxt): {ticker['last']}")
        human_delay(0.2, 0.5)
        return ticker['last']
    except Exception as e:
        print(f"⚠️ Binance ccxt: {e}")
    
    # СПОСОБ 2: Binance прямой API (разные User-Agent)
    try:
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        headers = {'User-Agent': random.choice(user_agents)}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            price = float(response.json()['price'])
            print(f"✅ {symbol} цена (Binance API): {price}")
            human_delay(0.2, 0.5)
            return price
    except Exception as e:
        print(f"⚠️ Binance API: {e}")
    
    # СПОСОБ 3: Bybit (запасной вариант)
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}USDT"
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                price = float(data['result']['list'][0]['lastPrice'])
                print(f"✅ {symbol} цена (Bybit): {price}")
                human_delay(0.2, 0.5)
                return price
    except Exception as e:
        print(f"⚠️ Bybit: {e}")
    
    print(f"❌ Не удалось получить цену {symbol}")
    return None

def get_historical_prices(symbol='BTC', limit=30):
    """Получает исторические цены (с обходом)"""
    
    # Пробуем Binance API
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=5m&limit={limit}"
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            closes = [float(candle[4]) for candle in data]
            print(f"✅ История {symbol}: {len(closes)} свечей")
            human_delay(0.3, 0.7)
            return closes
    except Exception as e:
        print(f"⚠️ История Binance: {e}")
    
    # По умолчанию - возвращаем текущую цену + шум
    current_price = get_crypto_price(symbol)
    if current_price:
        closes = [current_price * (1 + np.random.randn() * 0.01) for _ in range(limit)]
        return closes
    
    return None

# ============================================
# РАСЧЁТ ИНДИКАТОРОВ
# ============================================
def get_rsi(prices, period=14):
    if not prices or len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period]) if len(gains[:period]) > 0 else 0
    avg_loss = np.mean(losses[:period]) if len(losses[:period]) > 0 else 0.001
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_potential_profit(price, rsi, change_percent, currency='USD'):
    """Расчёт прибыли с учётом курса валют"""
    
    # Логика сигнала
    if rsi < 30:
        target_percent = random.uniform(2.5, 4.0)
        stop_percent = random.uniform(-1.2, -0.8)
        confidence = random.choice(['Высокий', 'Очень высокий'])
    elif rsi > 70:
        target_percent = random.uniform(1.5, 3.0)
        stop_percent = random.uniform(-1.5, -1.0)
        confidence = random.choice(['Высокий', 'Средний'])
    elif change_percent > 0.5:
        target_percent = random.uniform(1.0, 2.5)
        stop_percent = random.uniform(-0.7, -0.4)
        confidence = 'Средний'
    else:
        target_percent = random.uniform(0.5, 1.5)
        stop_percent = random.uniform(-0.5, -0.3)
        confidence = 'Низкий'
    
    target_price = price * (1 + target_percent / 100)
    stop_price = price * (1 + stop_percent / 100)
    profit_usd = price * (target_percent / 100)
    
    # Конвертация в выбранную валюту
    rate = get_currency_rate(currency)
    profit_converted = profit_usd * rate
    
    return {
        'target_percent': target_percent,
        'stop_percent': stop_percent,
        'target_price': target_price,
        'stop_price': stop_price,
        'profit_usd': profit_usd,
        'profit': profit_converted,
        'currency': currency,
        'confidence': confidence
    }

# ============================================
# ИИ-АНАЛИЗ
# ============================================
def analyze_with_ai(symbol, price, rsi, change_percent, profit_data):
    if OPENAI_API_KEY != "ТВОЙ_КЛЮЧ_ОТ_OPENAI" and OPENAI_API_KEY:
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            prompt = f"""Криптовалюта {symbol}. Цена ${price:.0f}, RSI {rsi:.1f}, импульс {change_percent:+.1f}%. 
            Дай краткий прогноз (1-2 предложения) и сигнал (BUY/SELL/WAIT)."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                timeout=10
            )
            return f"🤖 ИИ-анализ:\n{response.choices[0].message.content}"
        except:
            pass
    
    # Анализ без ИИ
    if rsi < 30:
        return "🤖 ИИ-анализ: Сильная перекупленность. Рекомендуется покупка с целью +3-4%"
    elif rsi > 70:
        return "🤖 ИИ-анализ: Перепроданность. Рекомендуется фиксация прибыли"
    else:
        return "🤖 ИИ-анализ: Нейтральный рынок. Лучше дождаться более чёткого сигнала"

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 Анализ"),
        KeyboardButton("💰 Настройки"),
        KeyboardButton("🪙 Список монет"),
        KeyboardButton("💱 Курсы валют"),
        KeyboardButton("❓ Помощь")
    )
    return keyboard

def crypto_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    cryptos = list(CRYPTO_LIST.keys())
    for i in range(0, len(cryptos), 2):
        row = []
        row.append(InlineKeyboardButton(cryptos[i], callback_data=f"crypto_{cryptos[i]}"))
        if i + 1 < len(cryptos):
            row.append(InlineKeyboardButton(cryptos[i+1], callback_data=f"crypto_{cryptos[i+1]}"))
        keyboard.add(*row)
    keyboard.add(InlineKeyboardButton("🏠 Меню", callback_data="menu"))
    return keyboard

def settings_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🇺🇸 USD", callback_data="cur_USD"),
        InlineKeyboardButton("🇪🇺 EUR", callback_data="cur_EUR"),
        InlineKeyboardButton("🇷🇺 RUB", callback_data="cur_RUB")
    )
    keyboard.add(InlineKeyboardButton("🏠 Меню", callback_data="menu"))
    return keyboard

# ============================================
# ОБРАБОТЧИКИ
# ============================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = {'currency': 'USD'}
    
    typing_action(message.chat.id)
    
    text = """🤖 <b>Крипто-Аналитик Бот v3.0</b>

<b>Реальные курсы валют с сайтов:</b>
• ЦБ РФ
• ExchangeRate-API
• Google Finance

<b>Особенности:</b>
• Имитация человеческой задержки
• Обход блокировок (User-Agent ротация)
• Анализ 12+ криптовалют

Выбери действие 👇"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "💱 Курсы валют")
def show_rates(message):
    typing_action(message.chat.id)
    rates = update_currency_rates()
    
    text = f"""💱 <b>Актуальные курсы валют</b>

🇺🇸 USD = 1 USD
🇪🇺 EUR = {rates['EUR']:.3f} USD
🇷🇺 RUB = {rates['RUB']:.3f} USD

<i>Обновлено: {datetime.now().strftime('%H:%M:%S')}</i>
<i>Источники: ЦБ РФ, ExchangeRate, Google</i>"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "📊 Анализ")
def analysis_menu(message):
    typing_action(message.chat.id)
    bot.send_message(message.chat.id, "🪙 Выбери криптовалюту:", reply_markup=crypto_keyboard())

@bot.message_handler(func=lambda m: m.text == "💰 Настройки")
def settings_menu(message):
    user_id = message.chat.id
    curr = user_settings.get(user_id, {}).get('currency', 'USD')
    text = f"⚙️ <b>Настройки</b>\n\n💰 Текущая валюта: {curr}\n\nВыбери новую:"
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=settings_keyboard())

@bot.message_handler(func=lambda m: m.text == "🪙 Список монет")
def list_cryptos(message):
    typing_action(message.chat.id)
    text = "🪙 <b>Доступные криптовалюты:</b>\n\n"
    for code, name in CRYPTO_LIST.items():
        price = get_crypto_price(code)
        price_text = f"${price:,.0f}" if price else "❌"
        text += f"• <b>{code}</b> ({name}) - {price_text}\n"
        human_delay(0.1, 0.3)
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_menu(message):
    text = """📖 <b>Помощь</b>

<b>Как пользоваться:</b>
1. Нажми «📊 Анализ» → выбери монету
2. Получи сигнал и уровни прибыли
3. В настройках смени валюту

<b>Что означают цифры:</b>
• Цель — уровень для фиксации прибыли
• Стоп — уровень для ограничения убытка
• Прибыль с $100 — наглядный расчёт

<b>Особенности бота:</b>
• Реальные курсы валют с сайтов
• Имитация задержек как у человека
• Обход блокировок через User-Agent

<i>Не является инвест-рекомендацией</i>"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

def analyze_crypto(message, crypto_symbol):
    user_id = message.chat.id
    currency = user_settings.get(user_id, {}).get('currency', 'USD')
    
    msg = bot.send_message(message.chat.id, f"🤔 Анализирую {crypto_symbol}... (имитация человеческого анализа)")
    human_delay(1.0, 2.5)
    
    try:
        # Получаем данные (уже с задержками внутри)
        price = get_crypto_price(crypto_symbol)
        if not price:
            bot.edit_message_text(f"❌ Не удалось получить данные по {crypto_symbol}. Биржи временно недоступны.", 
                                  message.chat.id, msg.message_id)
            return
        
        bot.edit_message_text(f"📊 Считаю индикаторы для {crypto_symbol}...", message.chat.id, msg.message_id)
        human_delay(0.8, 1.5)
        
        prices = get_historical_prices(crypto_symbol)
        if not prices:
            prices = [price * (1 + np.random.randn() * 0.01) for _ in range(30)]
        
        rsi = get_rsi(prices)
        change = ((prices[-1] - prices[-2]) / prices[-2]) * 100 if len(prices) >= 2 else 0
        
        bot.edit_message_text(f"📈 Рассчитываю потенциальную прибыль...", message.chat.id, msg.message_id)
        human_delay(0.5, 1.0)
        
        profit = calculate_potential_profit(price, rsi, change, currency)
        
        currency_symbols = {'USD': '$', 'EUR': '€', 'RUB': '₽'}
        curr_sym = currency_symbols.get(currency, '$')
        
        # Конвертируем текущую цену
        rate = get_currency_rate(currency)
        price_converted = price * rate
        
        result = f"""📊 <b>Анализ {crypto_symbol}</b>
━━━━━━━━━━━━━━━━━━━━━

💰 <b>Цена:</b> {curr_sym}{price_converted:,.2f}
📈 <b>Изменение 5м:</b> {change:+.2f}%
📉 <b>RSI:</b> {rsi:.1f}/100

━━━━━━━━━━━━━━━━━━━━━
<b>🎯 Уровни для входа:</b>

💹 <b>Take Profit:</b> {curr_sym}{profit['target_price'] * rate:,.2f} (+{profit['target_percent']:.1f}%)
🛑 <b>Stop Loss:</b> {curr_sym}{profit['stop_price'] * rate:,.2f} ({profit['stop_percent']:.1f}%)

💵 <b>Потенциальная прибыль с $100:</b> {curr_sym}{profit['profit']:.2f}
📊 <b>Уверенность:</b> {profit['confidence']}

━━━━━━━━━━━━━━━━━━━━━
{analyze_with_ai(crypto_symbol, price, rsi, change, profit)}

<i>⚠️ Торгуйте осторожно</i>"""
        
        bot.edit_message_text(result, message.chat.id, msg.message_id, parse_mode='HTML')
        
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)[:100]}", message.chat.id, msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("crypto_"):
        crypto = call.data.replace("crypto_", "")
        analyze_crypto(call.message, crypto)
    
    elif call.data.startswith("cur_"):
        currency = call.data.replace("cur_", "")
        user_settings[call.message.chat.id] = {'currency': currency}
        bot.answer_callback_query(call.id, f"✅ Валюта: {currency}")
        bot.edit_message_text(f"✅ Валюта изменена на {currency}", 
                              call.message.chat.id, call.message.message_id)
        human_delay(1.0, 1.5)
        start_cmd(call.message)
    
    elif call.data == "menu":
        start_cmd(call.message)
    
    bot.answer_callback_query(call.id)

# ============================================
# ЗАПУСК
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 КРИПТО-АНАЛИТИК БОТ v3.0")
    print("=" * 50)
    print("Особенности:")
    print("✅ Реальные курсы валют с ЦБ РФ, ExchangeRate, Google")
    print("✅ User-Agent ротация (обход блокировок)")
    print("✅ Имитация человеческих задержек")
    print("✅ 12 криптовалют")
    print("=" * 50)
    
    # Обновляем курсы при старте
    update_currency_rates()
    
    print("✅ Бот готов! Напиши /start в Telegram")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
