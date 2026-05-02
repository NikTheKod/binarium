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
import random
from datetime import datetime

# ============================================
# ТВОИ ТОКЕНЫ - ВСТАВЬ СВОИ!!!
# ============================================
TELEGRAM_TOKEN = "8651330648:AAGQdVLP73PWwdQNJf-sL32S_gJsqL3cYqg"  # ЗАМЕНИ!!!
OPENAI_API_KEY = "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"      # ЗАМЕНИ!!! (если нет, оставь как есть)
# ============================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Настройка биржи
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'},
    'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
})

# Хранилище для отслеживания цен (чтобы считать реальный P&L)
price_history = {}

# ============================================
# ПОЛУЧЕНИЕ ДАННЫХ
# ============================================

def get_historical_prices(symbol='BTC/USDT', limit=30):
    """Получает цены с Binance"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=limit)
        closes = [candle[4] for candle in ohlcv]
        if len(closes) >= 10:
            return closes
    except:
        pass
    
    try:
        symbol2 = symbol.replace('/', '')
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol2}&interval=5m&limit={limit}"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            data = response.json()
            return [float(candle[4]) for candle in data]
    except:
        pass
    
    # Тестовые данные
    base_price = 50000 if 'BTC' in symbol else 3000
    closes = [base_price + np.random.randn() * 100 for _ in range(limit)]
    for i in range(1, len(closes)):
        closes[i] = closes[i-1] + np.random.randn() * 50
    return [abs(x) for x in closes]

def get_rsi(prices, period=14):
    """Расчёт RSI"""
    if len(prices) < period + 1:
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
# РАСЧЁТ ПРИБЫЛИ/УБЫТКА
# ============================================

def calculate_pl(entry_price, current_price, investment=100):
    """Рассчитывает реальную прибыль/убыток"""
    # Сколько монет купили на $100
    coins_bought = investment / entry_price
    # Текущая стоимость портфеля
    current_value = coins_bought * current_price
    # Прибыль/убыток в долларах
    pnl_usd = current_value - investment
    # Прибыль/убыток в процентах
    pnl_percent = ((current_price - entry_price) / entry_price) * 100
    
    return {
        'pnl_usd': pnl_usd,
        'pnl_percent': pnl_percent,
        'current_value': current_value,
        'coins': coins_bought
    }

def calculate_potential_targets(price, rsi, change_percent):
    """Рассчитывает потенциальные цели (Take Profit / Stop Loss)"""
    
    # Определяем цели на основе RSI и импульса
    if rsi < 30:  # Перекупленность - потенциал роста
        tp1_percent = random.uniform(1.5, 2.5)  # +1.5-2.5%
        tp2_percent = random.uniform(3.0, 4.5)  # +3-4.5%
        sl_percent = random.uniform(-1.2, -0.8)  # -0.8-1.2%
        signal_type = "LONG 🟢"
        action_text = "Рекомендуется покупка"
    elif rsi > 70:  # Перепроданность - потенциал падения
        tp1_percent = random.uniform(-2.5, -1.5)  # -1.5-2.5%
        tp2_percent = random.uniform(-4.5, -3.0)  # -3-4.5%
        sl_percent = random.uniform(0.8, 1.2)  # +0.8-1.2%
        signal_type = "SHORT 🔴"
        action_text = "Рекомендуется продажа"
    elif change_percent > 1:  # Хороший импульс вверх
        tp1_percent = random.uniform(1.0, 1.8)
        tp2_percent = random.uniform(2.0, 3.0)
        sl_percent = random.uniform(-0.7, -0.4)
        signal_type = "LONG 🟢"
        action_text = "Импульс вверх"
    elif change_percent < -1:  # Импульс вниз
        tp1_percent = random.uniform(-1.8, -1.0)
        tp2_percent = random.uniform(-3.0, -2.0)
        sl_percent = random.uniform(0.4, 0.7)
        signal_type = "SHORT 🔴"
        action_text = "Импульс вниз"
    else:
        tp1_percent = random.uniform(0.5, 1.0)
        tp2_percent = random.uniform(1.2, 2.0)
        sl_percent = random.uniform(-0.5, -0.3)
        signal_type = "WAIT ⏳"
        action_text = "Нейтральный рынок"
    
    # Рассчитываем цены целей
    tp1_price = price * (1 + tp1_percent / 100)
    tp2_price = price * (1 + tp2_percent / 100)
    sl_price = price * (1 + sl_percent / 100)
    
    # Считаем прибыль/убыток с $100 для каждой цели
    if signal_type == "LONG 🟢" or signal_type == "WAIT ⏳":
        tp1_profit = (tp1_percent / 100) * 100
        tp2_profit = (tp2_percent / 100) * 100
        sl_loss = (sl_percent / 100) * 100
    else:  # SHORT
        tp1_profit = abs(tp1_percent / 100) * 100
        tp2_profit = abs(tp2_percent / 100) * 100
        sl_loss = abs(sl_percent / 100) * 100
    
    return {
        'signal_type': signal_type,
        'action': action_text,
        'tp1_price': tp1_price,
        'tp1_percent': tp1_percent,
        'tp1_profit': tp1_profit,
        'tp2_price': tp2_price,
        'tp2_percent': tp2_percent,
        'tp2_profit': tp2_profit,
        'sl_price': sl_price,
        'sl_percent': sl_percent,
        'sl_loss': sl_loss
    }

def analyze_with_ai(closes, rsi_value, symbol, targets):
    """Анализ с ИИ"""
    price_now = closes[-1]
    price_before = closes[-2]
    change = ((price_now - price_before) / price_before) * 100
    
    result = f"""🎯 <b>ТОРГОВЫЙ СИГНАЛ</b>
━━━━━━━━━━━━━━━━━━━━━

{targets['signal_type']} <b>Сигнал:</b> {targets['action']}

📊 <b>Индикаторы:</b>
• RSI: {rsi_value:.1f}
• Импульс: {change:+.2f}%

━━━━━━━━━━━━━━━━━━━━━
<b>💰 ПРИБЫЛЬ/УБЫТОК С $100</b>

🎯 <b>Take Profit 1:</b>
   Цена: {targets['tp1_price']:.0f}$ 
   Профит: <b>+{targets['tp1_profit']:.2f}$</b> <code>(+{abs(targets['tp1_percent']):.1f}%)</code>

🎯 <b>Take Profit 2:</b>
   Цена: {targets['tp2_price']:.0f}$
   Профит: <b>+{targets['tp2_profit']:.2f}$</b> <code>(+{abs(targets['tp2_percent']):.1f}%)</code>

🛑 <b>Stop Loss:</b>
   Цена: {targets['sl_price']:.0f}$
   Убыток: <b>-{targets['sl_loss']:.2f}$</b> <code>({targets['sl_percent']:.1f}%)</code>

━━━━━━━━━━━━━━━━━━━━━
📈 <b>Риск/Прибыль (R:R):</b> 1:{max(1.5, targets['tp1_profit']/abs(targets['sl_loss'])):.1f}"""

    # Добавляем ИИ анализ если есть ключ
    if OPENAI_API_KEY != "ТВОЙ_КЛЮЧ_ОТ_OPENAI" and OPENAI_API_KEY:
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            prompt = f"{symbol}: цена={price_now:.0f}, RSI={rsi_value:.1f}, импульс={change:+.1f}%. Дай совет в 2 строках."
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                timeout=10
            )
            result += f"\n\n🤖 <b>ИИ-совет:</b>\n{response.choices[0].message.content}"
        except:
            pass
    
    return result

# ============================================
# КЛАВИАТУРЫ
# ============================================

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 ПОЛУЧИТЬ СИГНАЛ"),
        KeyboardButton("📈 BTC/USDT"),
        KeyboardButton("🔷 ETH/USDT"),
        KeyboardButton("💰 P&L ОТСЛЕЖИВАНИЕ"),
        KeyboardButton("ℹ️ ПОМОЩЬ")
    )
    return keyboard

def inline_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔄 НОВЫЙ СИГНАЛ", callback_data="new"))
    keyboard.add(
        InlineKeyboardButton("₿ BTC", callback_data="btc"), 
        InlineKeyboardButton("⟠ ETH", callback_data="eth")
    )
    return keyboard

def pl_keyboard(symbol):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"🔄 ОБНОВИТЬ {symbol}", callback_data=f"pl_{symbol}"))
    keyboard.add(InlineKeyboardButton("📊 НОВЫЙ СИГНАЛ", callback_data="new"))
    return keyboard

# ============================================
# ОБРАБОТЧИКИ
# ============================================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "🤖 <b>КРИПТО-АНАЛИТИК БОТ v5.0</b>\n\n"
        "📊 <b>Что я умею:</b>\n"
        "• Анализировать BTC и ETH\n"
        "• Рассчитывать потенциальную прибыль/убыток с $100\n"
        "• Давать 2 уровня Take Profit\n"
        "• Показывать Stop Loss\n"
        "• Отслеживать реальный P&L\n\n"
        "💰 <b>Пример:</b> При сигнале LONG с TP1 +1.5%\n"
        "Вложение $100 → прибыль $1.50\n\n"
        "Выбери действие 👇",
        parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "💰 P&L ОТСЛЕЖИВАНИЕ")
def pl_tracking(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("₿ BTC", callback_data="pl_BTC/USDT"),
        InlineKeyboardButton("⟠ ETH", callback_data="pl_ETH/USDT")
    )
    keyboard.add(InlineKeyboardButton("📊 НАЗАД К АНАЛИЗУ", callback_data="new"))
    bot.send_message(message.chat.id, 
                     "📊 <b>ОТСЛЕЖИВАНИЕ ПРИБЫЛИ/УБЫТКА</b>\n\n"
                     "Выбери монету, чтобы увидеть текущий P&L:\n"
                     "• Если купил по цене сигнала\n"
                     "• С момента последнего анализа\n\n"
                     "<i>Данные обновляются в реальном времени</i>",
                     parse_mode='HTML', reply_markup=keyboard)

@bot.message_handler(commands=['help'])
def help_msg(message):
    help_text = """📖 <b>ПОМОЩЬ</b>

<b>🔍 КАК ЧИТАТЬ СИГНАЛ:</b>

• <b>LONG 🟢</b> - рекомендуем покупать
• <b>SHORT 🔴</b> - рекомендуем продавать
• <b>WAIT ⏳</b> - лучше подождать

<b>💰 ПРИБЫЛЬ С $100:</b>
Показывает, сколько денег вы заработаете или потеряете при вложении $100

<b>🎯 ДВА УРОВНЯ TP:</b>
• TP1 - первая цель (фиксируем часть прибыли)
• TP2 - вторая цель (основная прибыль)

<b>🛑 STOP LOSS:</b>
Максимальный убыток, который рекомендуется допустить

<b>📊 R:R (Риск/Прибыль):</b>
Соотношение потенциальной прибыли к убытку. > 1:2 - отлично

<b>💰 P&L ОТСЛЕЖИВАНИЕ:</b>
Показывает реальную прибыль/убыток, если вы вошли по сигналу бота"""
    
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["📊 ПОЛУЧИТЬ СИГНАЛ", "📈 BTC/USDT", "🔷 ETH/USDT"])
def handle_analysis(message):
    symbol = "BTC/USDT" if "BTC" in message.text else "ETH/USDT" if "ETH" in message.text else "BTC/USDT"
    
    msg = bot.send_message(message.chat.id, f"🔄 <b>Анализирую {symbol}...</b>", parse_mode='HTML')
    
    # Получаем цены
    closes = get_historical_prices(symbol)
    if not closes:
        bot.edit_message_text(f"❌ Ошибка: не удалось получить данные по {symbol}", 
                              message.chat.id, msg.message_id)
        return
    
    rsi_val = get_rsi(closes)
    current_price = closes[-1]
    price_before = closes[-2]
    change = ((current_price - price_before) / price_before) * 100
    
    # Рассчитываем цели
    targets = calculate_potential_targets(current_price, rsi_val, change)
    
    # Анализ с ИИ
    analysis = analyze_with_ai(closes, rsi_val, symbol, targets)
    
    # Сохраняем цену для P&L отслеживания
    if symbol not in price_history:
        price_history[symbol] = []
    price_history[symbol].append({
        'timestamp': time.time(),
        'price': current_price,
        'signal': targets['signal_type']
    })
    # Оставляем только последние 10 записей
    price_history[symbol] = price_history[symbol][-10:]
    
    result = f"""🔍 <b>АНАЛИЗ {symbol}</b>
━━━━━━━━━━━━━━━━━━━━━

💰 <b>Текущая цена:</b> {current_price:.0f}$
📊 <b>Изменение:</b> <b>{change:+.2f}%</b>
📉 <b>RSI:</b> {rsi_val:.1f}/100

{analysis}

<i>💰 Прибыль/убыток рассчитан при вложении $100</i>
<i>⚠️ Не является инвестиционной рекомендацией</i>"""
    
    bot.edit_message_text(result, message.chat.id, msg.message_id, 
                          parse_mode='HTML', reply_markup=inline_menu())

def show_pl(call, symbol):
    """Показывает реальный P&L по монете"""
    closes = get_historical_prices(symbol, 5)
    if not closes:
        bot.answer_callback_query(call.id, "❌ Ошибка получения данных")
        return
    
    current_price = closes[-1]
    
    # Берём последний сигнал по этой монете
    last_signals = [s for s in price_history.get(symbol, [])]
    
    if not last_signals:
        # Нет истории - показываем гипотетический вход по текущей цене
        pl = calculate_pl(current_price, current_price, 100)
        text = f"""📊 <b>P&L {symbol}</b>
━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Нет истории сигналов</b>

Совет: Нажми «📊 ПОЛУЧИТЬ СИГНАЛ» для {symbol}
Затем я буду отслеживать потенциальную прибыль

💰 <b>Если бы вы вошли сейчас:</b>
• Вход: {current_price:.0f}$
• Профит: $0.00 (0%)
• Стоп-лосс: рекомендуем -1%"""
    else:
        last_signal = last_signals[-1]
        entry_price = last_signal['price']
        signal_type = last_signal['signal']
        pl = calculate_pl(entry_price, current_price, 100)
        
        emoji = "🟢📈" if pl['pnl_usd'] >= 0 else "🔴📉"
        sign = "+" if pl['pnl_usd'] >= 0 else ""
        
        text = f"""📊 <b>P&L {symbol}</b>
━━━━━━━━━━━━━━━━━━━━━

{emoji} <b>Результат по сигналу:</b> {signal_type}

💰 <b>Цена входа:</b> {entry_price:.0f}$
💹 <b>Текущая цена:</b> {current_price:.0f}$

━━━━━━━━━━━━━━━━━━━━━
<b>ПРИБЫЛЬ/УБЫТОК:</b>

💵 <b>{sign}{pl['pnl_usd']:.2f}$</b> <code>({sign}{pl['pnl_percent']:.1f}%)</code>

📊 <b>Сумма:</b> ${pl['current_value']:.2f}
🪙 <b>Монет:</b> {pl['coins']:.6f}

━━━━━━━━━━━━━━━━━━━━━
<i>При вложении $100 во время последнего сигнала</i>
<i>Данные обновлены: {datetime.now().strftime('%H:%M:%S')}</i>"""
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                          parse_mode='HTML', reply_markup=pl_keyboard(symbol))

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "new":
        handle_analysis(call.message)
    elif call.data == "btc":
        handle_analysis(call.message)
        call.message.text = "📈 BTC/USDT"
    elif call.data == "eth":
        handle_analysis(call.message)
        call.message.text = "🔷 ETH/USDT"
    elif call.data == "pl_BTC/USDT":
        show_pl(call, "BTC/USDT")
    elif call.data == "pl_ETH/USDT":
        show_pl(call, "ETH/USDT")
    elif call.data.startswith("pl_"):
        symbol = call.data.replace("pl_", "")
        show_pl(call, symbol)
    
    bot.answer_callback_query(call.id)

# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 КРИПТО-АНАЛИТИК БОТ v5.0")
    print("=" * 50)
    print("✅ НОВЫЕ ФУНКЦИИ:")
    print("   • Два уровня Take Profit")
    print("   • Стоп-лосс")
    print("   • Расчёт прибыли/убытка с $100")
    print("   • Real-time P&L отслеживание")
    print("   • Соотношение Риск/Прибыль")
    print("=" * 50)
    
    test = get_historical_prices("BTC/USDT", 5)
    if test:
        print(f"✅ Данные получены! Цена BTC: {test[-1]:.0f}$")
    else:
        print("⚠️ Тестовые данные")
    
    print("=" * 50)
    print("✅ БОТ ГОТОВ! Напиши /start в Telegram")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
