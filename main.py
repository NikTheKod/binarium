# ============================================
# АВТОУСТАНОВКА БИБЛИОТЕК
# ============================================
import subprocess
import sys

packages = ['numpy', 'ccxt', 'pyTelegramBotAPI', 'requests', 'fake-useragent']
for package in packages:
    try:
        if package == 'pyTelegramBotAPI':
            __import__('telebot')
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
from datetime import datetime
from fake_useragent import UserAgent

# ============================================
# ТВОИ ТОКЕНЫ - ВСТАВЬ СВОИ!!!
# ============================================
TELEGRAM_TOKEN = "8651330648:AAGQdVLP73PWwdQNJf-sL32S_gJsqL3cYqg"  # ЗАМЕНИ!!!
OPENAI_API_KEY = "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"      # если нет - оставь, работает без ИИ
# ============================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ua = UserAgent()

# Список криптовалют
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

# Хранилище настроек пользователей
user_settings = {}
last_rate_update = None
currency_rates = {'USD': 1, 'EUR': 0.92, 'RUB': 91.5}  # запасные значения

# ============================================
# ИМИТАЦИЯ ЧЕЛОВЕКА (реалистичные задержки)
# ============================================

def human_delay(min_sec=0.5, max_sec=2.0):
    """Случайная задержка как у реального человека"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def typing_action(chat_id):
    """Имитация набора текста"""
    bot.send_chat_action(chat_id, 'typing')
    human_delay(0.3, 1.0)

def thinking_action(chat_id):
    """Имитация 'думает' (как будто анализирует)"""
    bot.send_chat_action(chat_id, 'typing')
    human_delay(1.0, 2.5)

def get_random_user_agent():
    """Возвращает случайный User-Agent как у реального браузера"""
    return ua.random

# ============================================
# ПОЛУЧЕНИЕ КУРСОВ ВАЛЮТ (реальные с сайтов)
# ============================================

def update_currency_rates():
    """Обновляет курсы валют с бесплатных API"""
    global currency_rates, last_rate_update
    
    # Обновляем раз в 30 минут
    if last_rate_update and datetime.now() - last_rate_update < timedelta(minutes=30):
        return currency_rates
    
    print("🔄 Обновляю курсы валют...")
    
    try:
        # Бесплатный API с курсами
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        headers = {'User-Agent': get_random_user_agent()}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            currency_rates['EUR'] = data['rates'].get('EUR', 0.92)
            currency_rates['RUB'] = data['rates'].get('RUB', 91.5)
            print(f"✅ Курсы обновлены: EUR={currency_rates['EUR']}, RUB={currency_rates['RUB']}")
            last_rate_update = datetime.now()
        else:
            print("⚠️ API не ответил, использую запасные курсы")
            
    except Exception as e:
        print(f"⚠️ Ошибка получения курсов: {e}")
    
    return currency_rates

def get_currency_rate(currency='USD'):
    """Возвращает курс валюты к USD"""
    rates = update_currency_rates()
    if currency == 'USD':
        return 1
    elif currency == 'EUR':
        return rates.get('EUR', 0.92)
    elif currency == 'RUB':
        return rates.get('RUB', 91.5)
    return 1

# ============================================
# ПОЛУЧЕНИЕ ДАННЫХ С БИРЖИ (с обходом)
# ============================================

def get_crypto_data(symbol='BTC'):
    """Получает текущую цену и историю с Binance"""
    
    try:
        # Создаём экземпляр биржи со случайным User-Agent
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'headers': {
                'User-Agent': get_random_user_agent(),
                'Accept': 'application/json',
            }
        })
        
        pair = f"{symbol}/USDT"
        
        # Получаем текущую цену
        ticker = exchange.fetch_ticker(pair)
        current_price = ticker['last']
        
        # Получаем историю цен (30 свечей по 5 минут)
        ohlcv = exchange.fetch_ohlcv(pair, timeframe='5m', limit=30)
        closes = [candle[4] for candle in ohlcv]
        
        print(f"✅ {symbol}: цена ${current_price:,.0f}, получено {len(closes)} свечей")
        return current_price, closes
        
    except Exception as e:
        print(f"❌ Ошибка получения {symbol}: {e}")
        return None, None

def get_rsi(prices, period=14):
    """Расчёт RSI индикатора"""
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

# ============================================
# РАСЧЁТ ПРИБЫЛИ
# ============================================

def calculate_profit(price, rsi, change_percent, currency='USD'):
    """Рассчитывает потенциальную прибыль и уровни"""
    
    # Определяем цели на основе RSI
    if rsi < 30:
        target_percent = random.uniform(2.5, 4.0)
        stop_percent = random.uniform(-1.2, -0.8)
        confidence = "Высокий 🟢"
        signal = "🟢 ПОКУПКА"
    elif rsi > 70:
        target_percent = random.uniform(1.8, 3.2)
        stop_percent = random.uniform(-1.3, -0.9)
        confidence = "Высокий 🔴"
        signal = "🔴 ПРОДАЖА"
    elif change_percent > 0.5:
        target_percent = random.uniform(1.2, 2.5)
        stop_percent = random.uniform(-0.8, -0.4)
        confidence = "Средний 📊"
        signal = "🟡 УМЕРЕННЫЙ РОСТ"
    elif change_percent < -0.5:
        target_percent = random.uniform(0.8, 1.8)
        stop_percent = random.uniform(-1.0, -0.5)
        confidence = "Средний 📊"
        signal = "🟡 УМЕРЕННОЕ ПАДЕНИЕ"
    else:
        target_percent = random.uniform(0.5, 1.2)
        stop_percent = random.uniform(-0.5, -0.3)
        confidence = "Низкий ⚪"
        signal = "⚪ НЕЙТРАЛЬНО"
    
    target_price = price * (1 + target_percent / 100)
    stop_price = price * (1 + stop_percent / 100)
    profit_usd = price * (target_percent / 100)
    
    # Конвертируем в выбранную валюту
    rate = get_currency_rate(currency)
    profit_converted = profit_usd * rate
    target_price_converted = target_price * rate
    stop_price_converted = stop_price * rate
    price_converted = price * rate
    
    return {
        'signal': signal,
        'target_percent': target_percent,
        'stop_percent': stop_percent,
        'target_price': target_price_converted,
        'stop_price': stop_price_converted,
        'profit': profit_converted,
        'price': price_converted,
        'currency': currency,
        'confidence': confidence
    }

# ============================================
# ИИ АНАЛИЗ (если есть ключ)
# ============================================

def ai_analysis(symbol, price, rsi, change_percent):
    """Анализ через ChatGPT"""
    if OPENAI_API_KEY and OPENAI_API_KEY != "ТВОЙ_КЛЮЧ_ОТ_OPENAI":
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            
            prompt = f"""Ты криптоаналитик. Дай краткий прогноз по {symbol}:
Цена: ${price:,.0f}
RSI: {rsi:.1f}
Импульс за 5 минут: {change_percent:+.1f}%

Ответь в 2-3 предложениях, дай сигнал (BUY/SELL/WAIT)."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                timeout=10
            )
            return f"🤖 <b>ИИ-анализ ChatGPT:</b>\n{response.choices[0].message.content}"
        except Exception as e:
            print(f"ИИ ошибка: {e}")
    
    # Без ИИ - используем логику
    if rsi < 30:
        return "🤖 <b>Анализ:</b> Сильная перекупленность. Хороший момент для покупки."
    elif rsi > 70:
        return "🤖 <b>Анализ:</b> Перепроданность. Рекомендуется фиксация прибыли."
    elif change_percent > 1:
        return "🤖 <b>Анализ:</b> Хороший восходящий импульс. Можно рассматривать вход."
    elif change_percent < -1:
        return "🤖 <b>Анализ:</b> Нисходящее движение. Лучше подождать."
    else:
        return "🤖 <b>Анализ:</b> Рынок спокойный. Рекомендуется наблюдение."

# ============================================
# КЛАВИАТУРЫ И МЕНЮ
# ============================================

def main_keyboard():
    """Главная клавиатура"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 АНАЛИЗ"),
        KeyboardButton("💰 НАСТРОЙКИ"),
        KeyboardButton("🪙 КРИПТОВАЛЮТЫ"),
        KeyboardButton("💱 КУРСЫ ВАЛЮТ"),
        KeyboardButton("❓ ПОМОЩЬ")
    )
    return keyboard

def crypto_keyboard():
    """Клавиатура выбора крипты"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    cryptos = list(CRYPTO_LIST.keys())
    for i in range(0, len(cryptos), 2):
        row = []
        row.append(InlineKeyboardButton(f"🪙 {cryptos[i]}", callback_data=f"crypto_{cryptos[i]}"))
        if i + 1 < len(cryptos):
            row.append(InlineKeyboardButton(f"🪙 {cryptos[i+1]}", callback_data=f"crypto_{cryptos[i+1]}"))
        keyboard.add(*row)
    keyboard.add(InlineKeyboardButton("🏠 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
    return keyboard

def settings_keyboard():
    """Клавиатура настроек валюты"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("🇺🇸 USD $", callback_data="cur_USD"),
        InlineKeyboardButton("🇪🇺 EUR €", callback_data="cur_EUR"),
        InlineKeyboardButton("🇷🇺 RUB ₽", callback_data="cur_RUB")
    )
    keyboard.add(InlineKeyboardButton("🏠 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
    return keyboard

def after_analysis_keyboard(crypto):
    """Кнопки после анализа"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔄 ОБНОВИТЬ", callback_data=f"refresh_{crypto}"),
        InlineKeyboardButton("🪙 ДРУГАЯ МОНЕТА", callback_data="select_crypto")
    )
    keyboard.add(InlineKeyboardButton("🏠 МЕНЮ", callback_data="main_menu"))
    return keyboard

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = {'currency': 'USD'}
    
    typing_action(message.chat.id)
    
    text = """🤖 <b>КРИПТО-АНАЛИТИК БОТ</b>

<b>📊 Что я умею:</b>
• Анализ 10+ криптовалют
• Расчёт потенциальной прибыли
• Уровни Take Profit и Stop Loss
• ИИ-анализ (ChatGPT)
• Реальные курсы валют

<b>💰 Пример:</b> При сигнале BUY с целью +3%
Вложение $100 → прибыль $3

<i>Выбери действие 👇</i>"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 АНАЛИЗ")
def analysis_menu(message):
    thinking_action(message.chat.id)
    bot.send_message(message.chat.id, "🪙 <b>Выбери криптовалюту для анализа:</b>", 
                     parse_mode='HTML', reply_markup=crypto_keyboard())

@bot.message_handler(func=lambda m: m.text == "💰 НАСТРОЙКИ")
def settings_menu(message):
    user_id = message.chat.id
    currency = user_settings.get(user_id, {}).get('currency', 'USD')
    
    text = f"""⚙️ <b>НАСТРОЙКИ</b>

💰 Текущая валюта: <b>{currency}</b>

<i>Прибыль будет отображаться в выбранной валюте</i>

Выбери новую валюту:"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=settings_keyboard())

@bot.message_handler(func=lambda m: m.text == "🪙 КРИПТОВАЛЮТЫ")
def list_cryptos(message):
    thinking_action(message.chat.id)
    
    text = "🪙 <b>ДОСТУПНЫЕ КРИПТОВАЛЮТЫ</b>\n\n"
    
    for code, name in CRYPTO_LIST.items():
        text += f"• <b>{code}</b> - {name}\n"
    
    text += "\n<i>Нажми «📊 АНАЛИЗ» для выбора монеты</i>"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "💱 КУРСЫ ВАЛЮТ")
def show_rates(message):
    thinking_action(message.chat.id)
    
    rates = update_currency_rates()
    
    text = f"""💱 <b>КУРСЫ ВАЛЮТ К USD</b>

🇺🇸 USD: <b>1.000</b>
🇪🇺 EUR: <b>{rates['EUR']:.3f}</b>
🇷🇺 RUB: <b>{rates['RUB']:.3f}</b>

<i>Обновлено: {datetime.now().strftime('%H:%M:%S')}</i>
<i>Источник: ExchangeRate-API</i>"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "❓ ПОМОЩЬ")
def help_menu(message):
    text = """📖 <b>ПОМОЩЬ</b>

<b>🔍 КАК ПОЛЬЗОВАТЬСЯ:</b>

1️⃣ Нажми «📊 АНАЛИЗ»
2️⃣ Выбери криптовалюту
3️⃣ Получи сигнал с целями

<b>📊 ЧТО ОЗНАЧАЮТ ЦИФРЫ:</b>

• <b>Take Profit</b> - уровень фиксации прибыли
• <b>Stop Loss</b> - уровень ограничения убытка
• <b>Прибыль с $100</b> - наглядный расчёт

<b>💰 НАСТРОЙКИ:</b>
Можно сменить валюту (USD/EUR/RUB)

<b>⚠️ ВАЖНО:</b>
Бот не даёт 100% гарантий. Торгуйте ответственно!"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ АНАЛИЗА
# ============================================

def analyze_crypto(message, crypto_symbol):
    user_id = message.chat.id
    currency = user_settings.get(user_id, {}).get('currency', 'USD')
    
    # Имитация человеческого мышления
    msg = bot.send_message(message.chat.id, f"🤔 <b>Анализирую {crypto_symbol}...</b>", parse_mode='HTML')
    thinking_action(message.chat.id)
    
    # Получаем данные с биржи
    current_price, closes = get_crypto_data(crypto_symbol)
    
    if not current_price or not closes:
        bot.edit_message_text(f"❌ <b>Ошибка!</b>\n\nНе удалось получить данные по {crypto_symbol}.\n\nПопробуй позже или выбери другую монету.", 
                              message.chat.id, msg.message_id, parse_mode='HTML')
        return
    
    # Имитация расчета индикаторов
    bot.edit_message_text(f"📊 <b>Рассчитываю индикаторы для {crypto_symbol}...</b>", 
                          message.chat.id, msg.message_id, parse_mode='HTML')
    thinking_action(message.chat.id)
    
    # Расчёт индикаторов
    rsi = get_rsi(closes)
    change_5m = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if len(closes) >= 2 else 0
    
    # Имитация расчета прибыли
    bot.edit_message_text(f"💰 <b>Рассчитываю потенциальную прибыль...</b>", 
                          message.chat.id, msg.message_id, parse_mode='HTML')
    thinking_action(message.chat.id)
    
    # Расчёт прибыли
    profit_data = calculate_profit(current_price, rsi, change_5m, currency)
    
    # Получаем ИИ-анализ
    ai_text = ai_analysis(crypto_symbol, current_price, rsi, change_5m)
    
    # Формируем финальный результат
    currency_symbols = {'USD': '$', 'EUR': '€', 'RUB': '₽'}
    curr_sym = currency_symbols.get(currency, '$')
    
    # Определяем цвет сигнала
    signal_color = ""
    if "ПОКУПКА" in profit_data['signal']:
        signal_color = "🟢"
    elif "ПРОДАЖА" in profit_data['signal']:
        signal_color = "🔴"
    elif "РОСТ" in profit_data['signal']:
        signal_color = "📈"
    elif "ПАДЕНИЕ" in profit_data['signal']:
        signal_color = "📉"
    else:
        signal_color = "⚪"
    
    result_text = f"""📊 <b>АНАЛИЗ {crypto_symbol}</b>
━━━━━━━━━━━━━━━━━━━━━━━

{signal_color} <b>Сигнал:</b> {profit_data['signal']}

💰 <b>Цена:</b> {curr_sym}{profit_data['price']:,.2f}
📈 <b>Изменение 5м:</b> {change_5m:+.2f}%
📉 <b>RSI:</b> {rsi:.1f}/100

━━━━━━━━━━━━━━━━━━━━━━━
<b>🎯 УРОВНИ ДЛЯ ВХОДА:</b>

💹 <b>Take Profit:</b> {curr_sym}{profit_data['target_price']:,.2f} <code>(+{profit_data['target_percent']:.1f}%)</code>
🛑 <b>Stop Loss:</b> {curr_sym}{profit_data['stop_price']:,.2f} <code>({profit_data['stop_percent']:.1f}%)</code>

💵 <b>Прибыль с $100:</b> {curr_sym}{profit_data['profit']:.2f}
📊 <b>Уверенность:</b> {profit_data['confidence']}

━━━━━━━━━━━━━━━━━━━━━━━
{ai_text}

<i>⚠️ Не является инвестиционной рекомендацией</i>"""
    
    human_delay(0.5, 1.0)
    bot.edit_message_text(result_text, message.chat.id, msg.message_id, 
                          parse_mode='HTML', reply_markup=after_analysis_keyboard(crypto_symbol))

# ============================================
# ОБРАБОТЧИКИ КНОПОК
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("crypto_"):
        crypto = call.data.replace("crypto_", "")
        analyze_crypto(call.message, crypto)
    
    elif call.data.startswith("refresh_"):
        crypto = call.data.replace("refresh_", "")
        analyze_crypto(call.message, crypto)
    
    elif call.data == "select_crypto":
        bot.edit_message_text("🪙 <b>Выбери криптовалюту:</b>", 
                              call.message.chat.id, call.message.message_id,
                              parse_mode='HTML', reply_markup=crypto_keyboard())
    
    elif call.data.startswith("cur_"):
        currency = call.data.replace("cur_", "")
        user_settings[call.message.chat.id] = {'currency': currency}
        bot.answer_callback_query(call.id, f"✅ Валюта изменена на {currency}")
        
        text = f"✅ <b>Валюта изменена на {currency}</b>\n\nТеперь прибыль будет показываться в {currency}.\n\nНажми «📊 АНАЛИЗ» для новых сигналов."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
        human_delay(1.0, 1.5)
        start_command(call.message)
    
    elif call.data == "main_menu":
        start_command(call.message)
    
    bot.answer_callback_query(call.id)

# ============================================
# ЗАПУСК БОТА
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 КРИПТО-АНАЛИТИК БОТ v4.0")
    print("=" * 50)
    print("✅ Функции:")
    print("   • Реальная имитация человека")
    print("   • Ротация User-Agent")
    print("   • 10 криптовалют")
    print("   • 3 валюты (USD/EUR/RUB)")
    print("   • Расчёт прибыли с $100")
    print("   • ИИ-анализ (ChatGPT)")
    print("=" * 50)
    
    # Обновляем курсы валют при старте
    update_currency_rates()
    
    print("✅ БОТ ГОТОВ! Напиши /start в Telegram")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
