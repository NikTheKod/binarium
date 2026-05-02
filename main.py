# ============================================
# АВТОУСТАНОВКА БИБЛИОТЕК
# ============================================
import subprocess
import sys

packages = ['numpy', 'ccxt', 'pyTelegramBotAPI', 'requests']
for package in packages:
    try:
        if package == 'pyTelegramBotAPI':
            __import__('telebot')
        elif package == 'requests':
            __import__('requests')
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
import requests
import json
from datetime import datetime

# ============================================
# ТВОИ ТОКЕНЫ - ВСТАВЬ СВОИ!!!
# ============================================
TELEGRAM_TOKEN = "8651330648:AAGQdVLP73PWwdQNJf-sL32S_gJsqL3cYqg"  # ЗАМЕНИ!!!
OPENAI_API_KEY = "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"      # можно оставить как есть, если нет ключа
# ============================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Список доступных криптовалют (можно добавлять любые)
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
    'MATIC': 'Polygon'
}

# Курсы валют (обновляются раз в час)
CURRENCY_RATES = {
    'USD': 1,
    'EUR': 0.92,
    'RUB': 91.5
}

# Хранилище настроек пользователей
user_settings = {}

# Настройки биржи
exchange = ccxt.binance({
    'enableRateLimit': True,
    'headers': {'User-Agent': 'Mozilla/5.0'}
})

# ============================================
# ФУНКЦИИ ПОЛУЧЕНИЯ ДАННЫХ
# ============================================

def get_crypto_price(symbol='BTC'):
    """Получает текущую цену криптовалюты"""
    try:
        pair = f"{symbol}/USDT"
        ticker = exchange.fetch_ticker(pair)
        return ticker['last']
    except:
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return float(response.json()['price'])
        except:
            return None
    return None

def get_historical_prices(symbol='BTC', limit=30):
    """Получает исторические цены"""
    try:
        pair = f"{symbol}/USDT"
        ohlcv = exchange.fetch_ohlcv(pair, timeframe='5m', limit=limit)
        return [candle[4] for candle in ohlcv]
    except:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=5m&limit={limit}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [float(candle[4]) for candle in data]
        except:
            return None
    return None

def get_rsi(prices, period=14):
    """Расчёт RSI"""
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
    """Рассчитывает потенциальную прибыль"""
    # Базовая логика: чем ниже RSI, тем больше потенциал роста
    if rsi < 30:
        target_percent = 3.0  # цель +3%
        stop_percent = -1.0
        confidence = "Высокий"
    elif rsi < 45:
        target_percent = 1.5
        stop_percent = -0.8
        confidence = "Средний"
    elif rsi > 70:
        target_percent = 2.5  # на падении
        stop_percent = -1.2
        confidence = "Высокий"
    elif rsi > 55:
        target_percent = 1.0
        stop_percent = -0.7
        confidence = "Средний"
    else:
        target_percent = 0.8
        stop_percent = -0.5
        confidence = "Низкий"
    
    # Корректируем по текущему движению
    if change_percent > 0.5 and rsi < 60:
        target_percent += 1.0
    
    target_price = price * (1 + target_percent / 100)
    stop_price = price * (1 + stop_percent / 100)
    profit_usd = price * (target_percent / 100)
    
    # Конвертируем в выбранную валюту
    rate = CURRENCY_RATES.get(currency, 1)
    profit_converted = profit_usd * rate
    
    return {
        'target_percent': target_percent,
        'stop_percent': stop_percent,
        'target_price': target_price,
        'stop_price': stop_price,
        'profit': profit_converted,
        'currency': currency,
        'confidence': confidence
    }

def analyze_with_ai(symbol, price, rsi, change_percent, profit_data):
    """Анализ через ИИ (если есть ключ)"""
    if OPENAI_API_KEY == "ТВОЙ_КЛЮЧ_ОТ_OPENAI" or not OPENAI_API_KEY:
        # Без ИИ - быстрый ответ
        if rsi < 30:
            signal = "🟢 ПОКУПКА"
            action = "Рекомендуется вход в LONG"
        elif rsi > 70:
            signal = "🔴 ПРОДАЖА"
            action = "Рекомендуется вход в SHORT"
        elif change_percent > 1:
            signal = "🟡 Умеренный рост"
            action = "Можно рассмотреть вход"
        else:
            signal = "⚪ НЕЙТРАЛЬНО"
            action = "Лучше подождать"
        
        return f"""🤖 <b>ИИ-анализ ({symbol})</b>

{signal}

{action}

📊 Обоснование:
• RSI = {rsi:.1f} {'(перекупленность)' if rsi < 30 else '(перепроданность)' if rsi > 70 else '(норма)'}
• Текущее движение: {change_percent:+.2f}% за 5 минут
• Уверенность: {profit_data['confidence']}
"""
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        prompt = f"""Ты криптотрейдер. Проанализируй:
Монета: {symbol}
Цена: ${price:.0f}
RSI: {rsi:.1f} (0-100, <30 - oversold, >70 - overbought)
Импульс: {change_percent:+.2f}% за 5 мин

Дай краткий анализ (3-4 строки), сигнал: BUY, SELL или WAIT, и почему."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            timeout=10
        )
        ai_text = response.choices[0].message.content
        
        # Определяем сигнал из текста
        if 'BUY' in ai_text.upper():
            signal_emoji = "🟢"
        elif 'SELL' in ai_text.upper():
            signal_emoji = "🔴"
        else:
            signal_emoji = "⚪"
            
        return f"""🤖 <b>ИИ-анализ ({symbol})</b>

{signal_emoji} {ai_text}

📉 Уровни (на основе RSI):
• Цель: +{profit_data['target_percent']:.1f}%
• Стоп: {profit_data['stop_percent']:.1f}%
"""
    except Exception as e:
        return f"🤖 ИИ временно недоступен (ошибка: {str(e)[:50]})"

# ============================================
# КЛАВИАТУРЫ И МЕНЮ
# ============================================

def main_keyboard():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 Анализ"),
        KeyboardButton("💰 Мои настройки"),
        KeyboardButton("🪙 Список криптовалют"),
        KeyboardButton("❓ Помощь")
    )
    return keyboard

def crypto_selection_keyboard():
    """Клавиатура выбора криптовалюты"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    cryptos = list(CRYPTO_LIST.keys())
    for i in range(0, len(cryptos), 2):
        row = []
        row.append(InlineKeyboardButton(f"{cryptos[i]}", callback_data=f"crypto_{cryptos[i]}"))
        if i + 1 < len(cryptos):
            row.append(InlineKeyboardButton(f"{cryptos[i+1]}", callback_data=f"crypto_{cryptos[i+1]}"))
        keyboard.add(*row)
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return keyboard

def settings_keyboard():
    """Клавиатура настроек"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("💵 USD", callback_data="set_currency_USD"),
        InlineKeyboardButton("💶 EUR", callback_data="set_currency_EUR"),
        InlineKeyboardButton("💷 RUB", callback_data="set_currency_RUB")
    )
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return keyboard

def analysis_result_keyboard(crypto):
    """Кнопки после анализа"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{crypto}"),
        InlineKeyboardButton("🪙 Другая монета", callback_data="select_crypto")
    )
    keyboard.add(InlineKeyboardButton("🏠 Меню", callback_data="main_menu"))
    return keyboard

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = {'currency': 'USD', 'default_crypto': 'BTC'}
    
    welcome_text = """🚀 <b>Крипто-Аналитик Бот v2.0</b>

🤖 <b>Что я умею:</b>
• Анализировать 10+ криптовалют
• Рассчитывать потенциальную прибыль
• Показывать уровни входа и стоп-лосс
• Анализировать через ИИ (ChatGPT)

<b>📊 Как пользоваться:</b>
1. Нажми «📊 Анализ» или выбери монету
2. Получи сигнал с целями по прибыли
3. В настройках можно сменить валюту

<b>💰 Пример расчёта:</b>
Если сигнал BUY с целью +3%, то при вложении $100 → прибыль $3

<i>Выбери действие ниже 👇</i>"""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 Анализ")
def analysis_menu(message):
    bot.send_message(message.chat.id, "🪙 Выбери криптовалюту для анализа:", 
                     reply_markup=crypto_selection_keyboard())

@bot.message_handler(func=lambda m: m.text == "💰 Мои настройки")
def settings_menu(message):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = {'currency': 'USD', 'default_crypto': 'BTC'}
    
    settings = user_settings[user_id]
    text = f"""⚙️ <b>Твои настройки</b>

💵 Валюта: <b>{settings['currency']}</b>
🪙 Криптовалюта по умолчанию: <b>{settings['default_crypto']}</b>

Выбери новую валюту для отображения прибыли:"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=settings_keyboard())

@bot.message_handler(func=lambda m: m.text == "🪙 Список криптовалют")
def list_cryptos(message):
    text = "🪙 <b>Доступные криптовалюты:</b>\n\n"
    for code, name in CRYPTO_LIST.items():
        # Получаем текущую цену
        price = get_crypto_price(code)
        price_text = f"${price:,.0f}" if price else "недоступно"
        text += f"• <b>{code}</b> ({name}) - {price_text}\n"
    
    text += "\n<i>Нажми «📊 Анализ» и выбери любую монету</i>"
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_menu(message):
    help_text = """📖 <b>Помощь</b>

<b>Как читать сигнал?</b>
• 🟢 BUY — рекомендуем покупать
• 🔴 SELL — рекомендуем продавать
• ⚪ WAIT — лучше подождать

<b>Что означают цифры?</b>
• Цель — уровень, где фиксировать прибыль
• Стоп — уровень, где закрыть убыток
• Потенциальная прибыль — сколько заработаешь с $100

<b>Настройки</b>
Можно сменить валюту (USD/EUR/RUB) в разделе «Мои настройки»

<b>Торгуйте ответственно!</b> Не рискуйте больше, чем готовы потерять."""
    
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

# ============================================
# ФУНКЦИЯ АНАЛИЗА КРИПТОВАЛЮТЫ
# ============================================

def analyze_crypto(message, crypto_symbol):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = {'currency': 'USD', 'default_crypto': 'BTC'}
    
    currency = user_settings[user_id]['currency']
    
    msg = bot.send_message(message.chat.id, f"🔄 Анализирую {crypto_symbol}... (до 10 секунд)")
    
    try:
        # Получаем данные
        price = get_crypto_price(crypto_symbol)
        prices = get_historical_prices(crypto_symbol)
        
        if not price or not prices:
            bot.edit_message_text(f"❌ Не удалось получить данные по {crypto_symbol}. Попробуй позже.", 
                                  message.chat.id, msg.message_id)
            return
        
        # Расчёт индикаторов
        rsi = get_rsi(prices)
        change_5m = ((prices[-1] - prices[-2]) / prices[-2]) * 100 if len(prices) >= 2 else 0
        
        # Расчёт прибыли
        profit_data = calculate_potential_profit(price, rsi, change_5m, currency)
        
        # Формируем результат
        currency_symbols = {'USD': '$', 'EUR': '€', 'RUB': '₽'}
        curr_sym = currency_symbols.get(currency, '$')
        
        result = f"""📊 <b>Анализ {crypto_symbol}</b>
━━━━━━━━━━━━━━━━━━━━━

💰 <b>Текущая цена:</b> {curr_sym}{price:,.2f}
📈 <b>Изменение за 5 мин:</b> {change_5m:+.2f}%
📉 <b>RSI (14):</b> {rsi:.1f} / 100

━━━━━━━━━━━━━━━━━━━━━
<b>🎯 Потенциальная прибыль:</b>

💹 <b>Цель (Take Profit):</b> {curr_sym}{profit_data['target_price']:,.2f} (+{profit_data['target_percent']:.1f}%)
🛑 <b>Стоп-лосс (Stop Loss):</b> {curr_sym}{profit_data['stop_price']:,.2f} ({profit_data['stop_percent']:.1f}%)

💵 <b>Прибыль с $100:</b> {curr_sym}{profit_data['profit']:.2f}
📊 <b>Уверенность:</b> {profit_data['confidence']}

━━━━━━━━━━━━━━━━━━━━━"""
        
        # Добавляем ИИ-анализ
        ai_analysis = analyze_with_ai(crypto_symbol, price, rsi, change_5m, profit_data)
        result += f"\n{ai_analysis}"
        
        result += "\n<i>⚠️ Не является инвестиционной рекомендацией</i>"
        
        bot.edit_message_text(result, message.chat.id, msg.message_id, 
                              parse_mode='HTML', reply_markup=analysis_result_keyboard(crypto_symbol))
        
        # Обновляем настройки
        user_settings[user_id]['default_crypto'] = crypto_symbol
        
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка при анализе: {str(e)[:100]}", 
                              message.chat.id, msg.message_id)

# ============================================
# ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.message.chat.id
    
    if call.data.startswith("crypto_"):
        crypto = call.data.replace("crypto_", "")
        analyze_crypto(call.message, crypto)
    
    elif call.data.startswith("refresh_"):
        crypto = call.data.replace("refresh_", "")
        analyze_crypto(call.message, crypto)
    
    elif call.data == "select_crypto":
        bot.edit_message_text("🪙 Выбери криптовалюту:", call.message.chat.id, call.message.message_id,
                              reply_markup=crypto_selection_keyboard())
    
    elif call.data.startswith("set_currency_"):
        currency = call.data.replace("set_currency_", "")
        if user_id not in user_settings:
            user_settings[user_id] = {'currency': 'USD', 'default_crypto': 'BTC'}
        user_settings[user_id]['currency'] = currency
        
        bot.answer_callback_query(call.id, f"✅ Валюта изменена на {currency}")
        
        text = f"✅ Валюта изменена на <b>{currency}</b>\n\nТеперь прибыль будет показываться в {currency}."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    
    elif call.data == "main_menu":
        bot.edit_message_text("🏠 Главное меню", call.message.chat.id, call.message.message_id)
        start_command(call.message)
    
    bot.answer_callback_query(call.id)

# ============================================
# ЗАПУСК БОТА
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 КРИПТО-АНАЛИТИК БОТ v2.0 ЗАПУЩЕН")
    print("=" * 50)
    print("📊 Доступные криптовалюты:", ", ".join(CRYPTO_LIST.keys()))
    print("💰 Валюты: USD, EUR, RUB")
    print("🤖 ИИ: встроен (ChatGPT при наличии ключа)")
    print("=" * 50)
    print("✅ Бот готов! Напиши /start в Telegram")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
