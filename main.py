# ЭТА ЧАСТЬ САМА УСТАНОВИТ БИБЛИОТЕКИ НА REPLIT
import subprocess
import sys
import os

def install_package(package):
    try:
        __import__(package.split('==')[0])
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Устанавливаем нужные пакеты
install_package('numpy')
install_package('ccxt')
install_package('openai==0.28')
install_package('pyTelegramBotAPI')

# Теперь импортируем
import telebot
import openai
import ccxt
import numpy as np
from datetime import datetime

# ===== ТВОИ ТОКЕНЫ (ЗАМЕНИ НА СВОИ) =====
TELEGRAM_TOKEN = "8651330648:AAGQdVLP73PWwdQNJf-sL32S_gJsqL3cYqg"  # <- это пример, ВСТАВЬ СВОЙ!
OPENAI_API_KEY = "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"      # <- это пример, ВСТАВЬ СВОЙ!
# ========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY
exchange = ccxt.binance()

# Функция расчёта RSI
def get_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Получаем цены с Binance
def get_crypto_data(symbol='BTC/USDT', limit=30):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=limit)
    closes = [candle[4] for candle in ohlcv]
    return closes

# Анализ через OpenAI
def analyze_with_ai(closes, rsi_value):
    price_now = closes[-1]
    price_before = closes[-2]
    change = ((price_now - price_before) / price_before) * 100

    prompt = f"""Ты трейдер. Данные:
Цена: {price_now}
Изменение за 5 мин: {change:.2f}%
RSI: {rsi_value:.1f}
Последние цены: {closes[-5:]}

Ответь ТОЛЬКО в формате:
Сигнал: BUY/SELL/WAIT
Уверенность: 0-100%
Причина: коротко
Куда пойдёт через 5 мин: вверх/вниз/флет"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка: {str(e)}"

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! Жми /signal")

@bot.message_handler(commands=['signal'])
def send_signal(message):
    bot.reply_to(message, "🔄 Загружаю данные...")
    try:
        closes = get_crypto_data()
        rsi_val = get_rsi(closes)
        analysis = analyze_with_ai(closes, rsi_val)
        bot.reply_to(message, f"🤖 Прогноз:\n\n{analysis}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Запуск
if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()
