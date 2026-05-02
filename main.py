# ============================================
# АВТОУСТАНОВКА БИБЛИОТЕК (если их нет)
# ============================================
import subprocess
import sys
import os

packages = ['numpy', 'ccxt', 'openai==0.28', 'pyTelegramBotAPI']
for package in packages:
    try:
        if package.startswith('openai'):
            __import__('openai')
        elif package == 'numpy':
            __import__('numpy')
        elif package == 'ccxt':
            __import__('ccxt')
        else:
            __import__('telebot')
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# ============================================
# ИМПОРТЫ
# ============================================
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import openai
import ccxt
import numpy as np
import time
import threading

# ============================================
# ТВОИ ТОКЕНЫ - ВСТАВЬ СВОИ ЗНАЧЕНИЯ!!!
# ============================================
TELEGRAM_TOKEN = "8651330648:AAGQdVLP73PWwdQNJf-sL32S_gJsqL3cYqg"
OPENAI_API_KEY = "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"
# ============================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot'
    }
})

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_rsi(prices, period=14):
    """Расчёт RSI индикатора"""
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_crypto_data(symbol='BTC/USDT', limit=30):
    """Получение цен с Binance"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=limit)
        closes = [candle[4] for candle in ohlcv]
        return closes
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return None

def analyze_with_ai(closes, rsi_value):
    """Анализ через OpenAI"""
    if closes is None or len(closes) < 5:
        return "❌ Не удалось получить данные с биржи"
    
    price_now = closes[-1]
    price_before = closes[-2]
    change = ((price_now - price_before) / price_before) * 100
    
    # Определяем простой тренд без ИИ
    trend = "флет"
    if change > 0.3:
        trend = "вверх"
    elif change < -0.3:
        trend = "вниз"
    
    # Определяем сигнал на основе RSI
    signal = "WAIT"
    if rsi_value < 30:
        signal = "BUY (перекупленность)"
    elif rsi_value > 70:
        signal = "SELL (перепроданность)"
    elif change > 0.5:
        signal = "BUY (импульс вверх)"
    elif change < -0.5:
        signal = "SELL (импульс вниз)"
    
    prompt = f"""Ты трейдер-аналитик. Проанализируй данные:
Текущая цена: {price_now:.2f} USDT
Изменение за 5 минут: {change:.2f}%
RSI (14 периодов): {rsi_value:.1f}
(RSI < 30 - перекуплено, > 70 - перепродано)
Предыдущие 5 цен: {[round(x,2) for x in closes[-5:]]}

На основе этих данных дай прогноз. Ответь строго в формате:
📊 СИГНАЛ: [BUY/SELL/WAIT]
🎯 УВЕРЕННОСТЬ: [0-100]%
📝 ПРИЧИНА: [одна короткая фраза]
📈 ПРОГНОЗ НА 5 МИН: [вверх/вниз/флет]"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=15
        )
        result = response.choices[0].message.content
        return result
    except Exception as e:
        # Если OpenAI не работает, возвращаем анализ на основе индикаторов
        return f"""📊 СИГНАЛ: {signal}
🎯 УВЕРЕННОСТЬ: {65 if signal != 'WAIT' else 40}%
📝 ПРИЧИНА: RSI={rsi_value:.1f}, изменение={change:.1f}%
📈 ПРОГНОЗ НА 5 МИН: {trend}

⚠️ (Анализ на основе индикаторов, т.к. OpenAI временно недоступен)"""

# ============================================
# КЛАВИАТУРЫ И МЕНЮ
# ============================================

def main_keyboard():
    """Главная клавиатура с кнопками"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = KeyboardButton("📊 Получить сигнал")
    btn2 = KeyboardButton("📈 BTC/USDT")
    btn3 = KeyboardButton("ETH/USDT")
    btn4 = KeyboardButton("ℹ️ Помощь")
    keyboard.add(btn1, btn2, btn3, btn4)
    return keyboard

def inline_menu():
    """Инлайн-кнопки под сообщением"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_signal = InlineKeyboardButton("📊 Новый сигнал", callback_data="new_signal")
    btn_btc = InlineKeyboardButton("₿ BTC/USDT", callback_data="pair_btc")
    btn_eth = InlineKeyboardButton("⟠ ETH/USDT", callback_data="pair_eth")
    btn_help = InlineKeyboardButton("❓ Помощь", callback_data="help")
    keyboard.add(btn_signal, btn_btc, btn_eth, btn_help)
    return keyboard

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def start_message(message):
    welcome_text = """🤖 <b>Крипто-Аналитик Бот</b>

Я анализирую график <b>BTC/USDT</b> и <b>ETH/USDT</b> с помощью:
• RSI индикатора
• Анализа ценового движения
• Искусственного интеллекта (ChatGPT)

<b>Как пользоваться:</b>
Нажми на кнопку «📊 Получить сигнал» или выбери криптовалюту.

⚠️ <i>Не является инвестиционной рекомендацией. Торгуйте осторожно!</i>"""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def help_message(message):
    help_text = """📖 <b>Помощь</b>

<b>Доступные команды:</b>
/start - Перезапустить бота
/help - Это сообщение
/signal - Получить сигнал по BTC/USDT

<b>Кнопки:</b>
📊 Получить сигнал - Анализ BTC/USDT
📈 BTC/USDT - Анализ Биткоина
ETH/USDT - Анализ Эфириума

<b>Как это работает?</b>
Бот берёт цены с Binance, рассчитывает RSI и отправляет в ChatGPT для анализа.

<i>Вопросы и предложения: @ваш_ник</i>"""
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

@bot.message_handler(commands=['signal'])
def signal_command(message):
    send_analysis(message.chat.id, "BTC/USDT")

@bot.message_handler(func=lambda message: message.text == "📊 Получить сигнал")
def btn_signal(message):
    send_analysis(message.chat.id, "BTC/USDT")

@bot.message_handler(func=lambda message: message.text == "📈 BTC/USDT")
def btn_btc(message):
    send_analysis(message.chat.id, "BTC/USDT")

@bot.message_handler(func=lambda message: message.text == "ETH/USDT")
def btn_eth(message):
    send_analysis(message.chat.id, "ETH/USDT")

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def btn_help(message):
    help_message(message)

# ============================================
# ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "new_signal":
        send_analysis(call.message.chat.id, "BTC/USDT")
    elif call.data == "pair_btc":
        send_analysis(call.message.chat.id, "BTC/USDT")
    elif call.data == "pair_eth":
        send_analysis(call.message.chat.id, "ETH/USDT")
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        help_message(call.message)
    
    bot.answer_callback_query(call.id)

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ АНАЛИЗА
# ============================================

def send_analysis(chat_id, symbol="BTC/USDT"):
    """Отправляет анализ"""
    # Отправляем сообщение о начале анализа
    msg = bot.send_message(chat_id, f"🔄 Анализирую {symbol}... Пожалуйста, подождите 5-10 секунд")
    
    try:
        # Получаем данные
        closes = get_crypto_data(symbol)
        if closes is None or len(closes) < 20:
            bot.edit_message_text("❌ Ошибка: Не удалось получить данные с биржи. Попробуйте позже.", 
                                  chat_id, msg.message_id)
            return
        
        # Считаем RSI
        rsi_val = get_rsi(closes)
        
        # Анализ через ИИ
        analysis = analyze_with_ai(closes, rsi_val)
        
        # Формируем красивый ответ
        current_price = closes[-1]
        price_change = ((closes[-1] - closes[-2]) / closes[-2]) * 100
        
        result_text = f"""🔍 <b>Анализ {symbol}</b>
💰 Текущая цена: <b>{current_price:.2f}$</b>
📊 Изменение за 5 мин: <b>{price_change:+.2f}%</b>
📉 RSI (14): <b>{rsi_val:.1f}</b>

{analysis}

━━━━━━━━━━━━━━━━
<i>Нажми на кнопку ниже для нового сигнала</i>"""
        
        bot.edit_message_text(result_text, chat_id, msg.message_id, 
                              parse_mode='HTML', reply_markup=inline_menu())
        
    except Exception as e:
        error_text = f"❌ Произошла ошибка:\n{str(e)[:200]}\n\nПопробуйте позже."
        bot.edit_message_text(error_text, chat_id, msg.message_id)

# ============================================
# ЗАПУСК БОТА
# ============================================

def main():
    print("=" * 40)
    print("🤖 БОТ ЗАПУЩЕН")
    print("=" * 40)
    print(f"Telegram token: {TELEGRAM_TOKEN[:10]}...")
    print(f"OpenAI key: {OPENAI_API_KEY[:15] if OPENAI_API_KEY != 'ТВОЙ_КЛЮЧ_ОТ_OPENAI_API' else 'НЕ УСТАНОВЛЕН'}...")
    print("=" * 40)
    print("Бот готов к работе! Напиши /start в Telegram")
    print("=" * 40)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
