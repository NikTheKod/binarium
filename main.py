import telebot
import openai
import ccxt
import time
import numpy as np

# ===== НАСТРОЙКИ =====
TELEGRAM_TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER"
OPENAI_API_KEY = "ТВОЙ_КЛЮЧ_ОТ_OPENAI"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY
exchange = ccxt.binance()
# =====================

def get_rsi(prices, period=14):
    """Быстрый расчёт RSI (индикатор перекупленности)"""
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

def get_crypto_data(symbol='BTC/USDT', limit=30):
    """Берёт последние цены с Binance"""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=limit)
    closes = [candle[4] for candle in ohlcv]
    return closes

def analyze_with_ai(closes, rsi_value):
    """Просит OpenAI сказать, куда пойдёт цена"""
    price_now = closes[-1]
    price_before = closes[-2]
    change = ((price_now - price_before) / price_before) * 100

    prompt = f"""
Ты трейдер-аналитик. Проанализируй данные:
- Текущая цена: {price_now}
- Изменение за последние 5 мин: {change:.2f}%
- RSI (индикатор моментума): {rsi_value:.1f}
- Предыдущие 5 цен: {closes[-5:]}

Ответь строго в формате:
Сигнал: BUY / SELL / WAIT
Уверенность: число от 0 до 100%
Причина: одна короткая фраза
Куда пойдёт через 5 минут: вверх/вниз/флет
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # или gpt-4, если есть
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка OpenAI: {str(e)}"

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Жми /signal — дам прогноз на основе ИИ")

@bot.message_handler(commands=['signal'])
def send_signal(message):
    bot.reply_to(message, "🔄 Гружу данные с Binance...")
    try:
        closes = get_crypto_data()
        rsi_val = get_rsi(closes)
        analysis = analyze_with_ai(closes, rsi_val)
        bot.reply_to(message, f"🤖 Анализ ИИ:\n\n{analysis}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Запускаем бота
if __name__ == "__main__":
    print("Бот запущен. Жми /signal в Telegram")
    bot.infinity_polling()
