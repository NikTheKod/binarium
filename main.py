# ============================================
# АВТОУСТАНОВКА БИБЛИОТЕК
# ============================================
import subprocess
import sys

packages = ['numpy', 'ccxt', 'pyTelegramBotAPI', 'requests', 'threading']
for package in packages:
    try:
        if package == 'pyTelegramBotAPI':
            __import__('telebot')
        elif package == 'threading':
            __import__('threading')
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
import threading
import json
import os
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

# Хранилище данных
user_data = {}  # {user_id: {'tracking': bool, 'alerts': dict, 'portfolio': dict}}
price_cache = {}

# Файл для сохранения настроек
SETTINGS_FILE = "user_settings.json"

def load_settings():
    global user_data
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                user_data = json.load(f)
        except:
            user_data = {}

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(user_data, f)

# ============================================
# ПОЛУЧЕНИЕ ДАННЫХ
# ============================================

def get_crypto_price(symbol='BTC'):
    """Получает текущую цену"""
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
    """Получает историю цен"""
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
# РАСЧЁТ РЕАЛЬНОЙ ПРИБЫЛИ (без $100)
# ============================================

def calculate_real_pl(entry_price, current_price, amount=0):
    """
    Рассчитывает реальную прибыль/убыток
    amount - количество монет (если 0, считаем для 1 монеты)
    """
    if amount == 0:
        # Показываем в процентах и абсолютном изменении для 1 монеты
        percent_change = ((current_price - entry_price) / entry_price) * 100
        abs_change = current_price - entry_price
        return {
            'percent': percent_change,
            'abs_change': abs_change,
            'current_price': current_price,
            'entry_price': entry_price
        }
    else:
        # Реальный P&L для портфеля
        current_value = amount * current_price
        entry_value = amount * entry_price
        pnl = current_value - entry_value
        pnl_percent = ((current_price - entry_price) / entry_price) * 100
        return {
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'current_value': current_value,
            'entry_value': entry_value
        }

# ============================================
# ФОНОВОЕ ОТСЛЕЖИВАНИЕ
# ============================================

def start_price_tracking(user_id):
    """Запускает фоновое отслеживание цены для пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {'tracking': False, 'alerts': {}, 'portfolio': {}}
    
    user_data[user_id]['tracking'] = True
    save_settings()
    
    # Запускаем поток отслеживания если ещё не запущен
    thread_name = f"tracker_{user_id}"
    if not any(t.name == thread_name for t in threading.enumerate()):
        tracker_thread = threading.Thread(target=price_tracker, args=(user_id,), name=thread_name, daemon=True)
        tracker_thread.start()

def stop_price_tracking(user_id):
    """Останавливает фоновое отслеживание"""
    if user_id in user_data:
        user_data[user_id]['tracking'] = False
        save_settings()

def price_tracker(user_id):
    """Фоновая функция отслеживания цены"""
    print(f"🔍 Запущен трекер для пользователя {user_id}")
    
    last_prices = {}
    alert_threshold = 1.0  # Оповещать при изменении на 1%
    
    while user_data.get(user_id, {}).get('tracking', False):
        try:
            # Проверяем BTC и ETH
            for symbol in ['BTC', 'ETH']:
                current_price = get_crypto_price(symbol)
                if current_price:
                    # Если есть сохранённая цена
                    if symbol in last_prices:
                        old_price = last_prices[symbol]
                        change_percent = ((current_price - old_price) / old_price) * 100
                        
                        # Если изменение больше порога
                        if abs(change_percent) >= alert_threshold:
                            # Отправляем уведомление
                            direction = "🟢 ВВЕРХ" if change_percent > 0 else "🔴 ВНИЗ"
                            emoji = "📈" if change_percent > 0 else "📉"
                            
                            alert_text = f"""<b>{emoji} {symbol}/USDT - {direction}</b>

💰 <b>Было:</b> ${old_price:,.0f}
💰 <b>Стало:</b> ${current_price:,.0f}
📊 <b>Изменение:</b> <b>{change_percent:+.2f}%</b>

🕐 {datetime.now().strftime('%H:%M:%S')}"""
                            
                            try:
                                bot.send_message(user_id, alert_text, parse_mode='HTML')
                            except:
                                pass
                            
                            # Обновляем цену
                            last_prices[symbol] = current_price
                    else:
                        # Первый запуск - сохраняем цену
                        last_prices[symbol] = current_price
            
            # Проверяем портфель пользователя (если есть активные позиции)
            portfolio = user_data.get(user_id, {}).get('portfolio', {})
            for symbol, position in portfolio.items():
                if position.get('active', False):
                    current_price = get_crypto_price(symbol)
                    if current_price:
                        entry = position['entry_price']
                        change = ((current_price - entry) / entry) * 100
                        
                        # Оповещаем при достижении целей
                        if 'tp1' in position and current_price >= position['tp1'] and not position.get('tp1_alerted', False):
                            bot.send_message(user_id, f"🎯 <b>ЦЕЛЬ 1 ДОСТИГНУТА!</b>\n{symbol}: +{change:.1f}%\nПрибыль: ${calculate_real_pl(entry, current_price, position['amount'])['pnl']:.2f}", parse_mode='HTML')
                            user_data[user_id]['portfolio'][symbol]['tp1_alerted'] = True
                            save_settings()
                        
                        if 'sl' in position and current_price <= position['sl'] and not position.get('sl_alerted', False):
                            bot.send_message(user_id, f"🛑 <b>СТОП-ЛОСС СРАБОТАЛ!</b>\n{symbol}: {change:.1f}%\nУбыток: ${calculate_real_pl(entry, current_price, position['amount'])['pnl']:.2f}", parse_mode='HTML')
                            user_data[user_id]['portfolio'][symbol]['sl_alerted'] = True
                            save_settings()
            
        except Exception as e:
            print(f"Ошибка трекера: {e}")
        
        # Проверяем каждые 30 секунд
        time.sleep(30)
    
    print(f"🔴 Трекер для {user_id} остановлен")

# ============================================
# КЛАВИАТУРЫ
# ============================================

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 АНАЛИЗ"),
        KeyboardButton("💰 МОЙ ПОРТФЕЛЬ"),
        KeyboardButton("🔔 ФОНОВЫЙ РЕЖИМ"),
        KeyboardButton("ℹ️ ПОМОЩЬ")
    )
    return keyboard

def crypto_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("₿ BTC/USDT", callback_data="analyze_BTC"),
        InlineKeyboardButton("⟠ ETH/USDT", callback_data="analyze_ETH")
    )
    keyboard.add(InlineKeyboardButton("🏠 МЕНЮ", callback_data="menu"))
    return keyboard

def tracking_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔔 ВКЛЮЧИТЬ", callback_data="tracking_on"),
        InlineKeyboardButton("🔕 ВЫКЛЮЧИТЬ", callback_data="tracking_off")
    )
    keyboard.add(InlineKeyboardButton("📊 Статус", callback_data="tracking_status"))
    return keyboard

def portfolio_keyboard(symbol=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    if symbol:
        keyboard.add(
            InlineKeyboardButton("📈 Добавить позицию", callback_data=f"add_pos_{symbol}"),
            InlineKeyboardButton("❌ Закрыть позицию", callback_data=f"close_pos_{symbol}")
        )
    keyboard.add(InlineKeyboardButton("📊 НОВЫЙ АНАЛИЗ", callback_data="new_analyze"))
    keyboard.add(InlineKeyboardButton("🏠 МЕНЮ", callback_data="menu"))
    return keyboard

# ============================================
# ОБРАБОТЧИКИ
# ============================================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    if user_id not in user_data:
        user_data[user_id] = {'tracking': False, 'alerts': {}, 'portfolio': {}}
        save_settings()
    
    text = """🤖 <b>КРИПТО-ТРЕЙДЕР БОТ v6.0</b>

<b>📊 Что я умею:</b>
• Анализ BTC и ETH в реальном времени
• Расчёт реальной прибыли/убытка (не с $100)
• Фоновое отслеживание цены
• Оповещения о резких движениях
• Управление портфелем

<b>🔔 ФОНОВЫЙ РЕЖИМ:</b>
Бот сам присылает уведомления когда цена меняется на 1%+ даже если вы не в чате!

<b>💰 МОЙ ПОРТФЕЛЬ:</b>
Добавьте свои позиции и бот будет отслеживать реальную прибыль

Выберите действие 👇"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 АНАЛИЗ")
def analysis_menu(message):
    bot.send_message(message.chat.id, "🪙 Выберите криптовалюту для анализа:", 
                     reply_markup=crypto_keyboard())

@bot.message_handler(func=lambda m: m.text == "💰 МОЙ ПОРТФЕЛЬ")
def portfolio_menu(message):
    user_id = str(message.chat.id)
    portfolio = user_data.get(user_id, {}).get('portfolio', {})
    
    if not portfolio:
        text = """📊 <b>ВАШ ПОРТФЕЛЬ ПУСТ</b>

Чтобы добавить позицию:
1. Нажмите «📊 АНАЛИЗ»
2. Выберите монету
3. Нажмите «Добавить в портфель»

Бот будет автоматически отслеживать вашу прибыль/убыток!"""
    else:
        text = "<b>💰 ВАШ ПОРТФЕЛЬ</b>\n\n"
        total_pnl = 0
        for symbol, pos in portfolio.items():
            if pos.get('active', False):
                current_price = get_crypto_price(symbol)
                if current_price:
                    pl_data = calculate_real_pl(pos['entry_price'], current_price, pos['amount'])
                    emoji = "🟢" if pl_data['pnl'] >= 0 else "🔴"
                    text += f"{emoji} <b>{symbol}/USDT</b>\n"
                    text += f"   Вход: ${pos['entry_price']:,.0f}\n"
                    text += f"   Сейчас: ${current_price:,.0f}\n"
                    text += f"   P&L: <b>{pl_data['pnl']:+.2f}$</b> ({pl_data['pnl_percent']:+.1f}%)\n"
                    text += f"   Количество: {pos['amount']:.4f}\n\n"
                    total_pnl += pl_data['pnl']
        
        text += f"━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>Общий P&L: {total_pnl:+.2f}$</b>"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', 
                     reply_markup=portfolio_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔔 ФОНОВЫЙ РЕЖИМ")
def tracking_menu(message):
    user_id = str(message.chat.id)
    is_tracking = user_data.get(user_id, {}).get('tracking', False)
    
    status = "🟢 ВКЛЮЧЕН" if is_tracking else "🔴 ВЫКЛЮЧЕН"
    text = f"""🔔 <b>ФОНОВОЕ ОТСЛЕЖИВАНИЕ</b>

Статус: {status}

<b>Что делает:</b>
• Следит за ценой BTC и ETH каждые 30 секунд
• Присылает уведомление при изменении на 1%+
• Работает даже когда вы не в чате с ботом

<b>Уведомления:</b>
• BTC/USDT и ETH/USDT
• Ваши активные позиции из портфеля
• Достижение целей и стоп-лоссов

Выберите действие:"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', 
                     reply_markup=tracking_keyboard())

@bot.message_handler(func=lambda m: m.text == "ℹ️ ПОМОЩЬ")
def help_menu(message):
    text = """📖 <b>ПОМОЩЬ</b>

<b>📊 АНАЛИЗ:</b>
Показывает реальную прибыль/убыток при покупке 1 монеты

<b>💰 МОЙ ПОРТФЕЛЬ:</b>
Добавляйте свои сделки и отслеживайте реальный P&L

<b>🔔 ФОНОВЫЙ РЕЖИМ:</b>
Включите и бот сам будет присылать уведомления о движении цены

<b>Как добавить позицию:</b>
1. Нажмите «📊 АНАЛИЗ»
2. Выберите монету
3. Нажмите «➕ Добавить в портфель»
4. Введите количество монет

Бот будет автоматически рассчитывать вашу прибыль!"""
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

def analyze_crypto(message, symbol):
    """Анализ монеты с реальным P&L"""
    current_price = get_crypto_price(symbol)
    if not current_price:
        bot.send_message(message.chat.id, f"❌ Не удалось получить цену {symbol}")
        return
    
    prices = get_historical_prices(symbol, 30)
    rsi = get_rsi(prices) if prices else 50
    
    # Определяем сигнал
    if rsi < 30:
        signal = "🟢 ПОКУПКА"
        action = "Хороший момент для входа"
    elif rsi > 70:
        signal = "🔴 ПРОДАЖА"
        action = "Рекомендуется фиксация"
    else:
        signal = "⚪ НЕЙТРАЛЬНО"
        action = "Лучше подождать"
    
    # Рассчитываем изменение за час
    if prices and len(prices) >= 12:
        hour_ago = prices[-12]
        hour_change = ((current_price - hour_ago) / hour_ago) * 100
    else:
        hour_change = 0
    
    # Реальная прибыль для 1 монеты
    if len(prices) >= 2:
        day_ago = prices[0]
        day_change = ((current_price - day_ago) / day_ago) * 100
    else:
        day_change = 0
    
    text = f"""📊 <b>АНАЛИЗ {symbol}/USDT</b>
━━━━━━━━━━━━━━━━━━━━━

💰 <b>Текущая цена:</b> ${current_price:,.0f}

📈 <b>Изменения:</b>
• За 5 мин: {((prices[-1] - prices[-2]) / prices[-2] * 100) if prices and len(prices) >= 2 else 0:+.2f}%
• За час: {hour_change:+.2f}%
• За день: {day_change:+.2f}%

📉 <b>RSI:</b> {rsi:.1f}/100

━━━━━━━━━━━━━━━━━━━━━
<b>🎯 СИГНАЛ:</b> {signal}
📝 {action}

<b>💰 ПРИБЫЛЬ/УБЫТОК (на 1 монету):</b>
• Если купили час назад: {hour_change:+.1f}% = ${current_price - (current_price/(1+hour_change/100)):+.0f}$
• Если купили вчера: {day_change:+.1f}% = ${current_price - (current_price/(1+day_change/100)):+.0f}$

━━━━━━━━━━━━━━━━━━━━━
<i>🕐 {datetime.now().strftime('%H:%M:%S')}</i>"""
    
    # Кнопки для добавления в портфель
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"➕ Добавить {symbol} в портфель", callback_data=f"add_{symbol}"))
    keyboard.add(InlineKeyboardButton("🏠 МЕНЮ", callback_data="menu"))
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.message.chat.id)
    
    if call.data.startswith("analyze_"):
        symbol = call.data.replace("analyze_", "")
        analyze_crypto(call.message, symbol)
    
    elif call.data.startswith("add_"):
        symbol = call.data.replace("add_", "")
        bot.answer_callback_query(call.id, f"Введите количество {symbol} в чат")
        bot.send_message(call.message.chat.id, 
                        f"📝 Введите количество {symbol} (например: 0.5)\n\nИли нажмите «1» для 1 монеты")
        # Сохраняем состояние
        user_data[user_id]['temp_symbol'] = symbol
        save_settings()
    
    elif call.data == "tracking_on":
        start_price_tracking(user_id)
        bot.answer_callback_query(call.id, "✅ Фоновый режим ВКЛЮЧЕН")
        bot.edit_message_text("🔔 <b>Фоновый режим активирован!</b>\n\nБот будет присылать уведомления при изменении цены на 1%+", 
                              call.message.chat.id, call.message.message_id, parse_mode='HTML')
    
    elif call.data == "tracking_off":
        stop_price_tracking(user_id)
        bot.answer_callback_query(call.id, "❌ Фоновый режим ВЫКЛЮЧЕН")
        bot.edit_message_text("🔕 <b>Фоновый режим выключен</b>\n\nУведомления больше приходить не будут", 
                              call.message.chat.id, call.message.message_id, parse_mode='HTML')
    
    elif call.data == "tracking_status":
        is_tracking = user_data.get(user_id, {}).get('tracking', False)
        status = "включен 🟢" if is_tracking else "выключен 🔴"
        bot.answer_callback_query(call.id, f"Фоновый режим {status}")
    
    elif call.data == "new_analyze":
        analysis_menu(call.message)
    
    elif call.data == "menu":
        start(call.message)
    
    bot.answer_callback_query(call.id)

# Обработка ввода количества монет
@bot.message_handler(func=lambda m: m.text.replace('.', '').replace('-', '').isdigit() and len(m.text) < 10)
def handle_amount(message):
    user_id = str(message.chat.id)
    if user_id in user_data and 'temp_symbol' in user_data[user_id]:
        symbol = user_data[user_id]['temp_symbol']
        amount = float(message.text)
        current_price = get_crypto_price(symbol)
        
        if current_price:
            # Сохраняем позицию
            if 'portfolio' not in user_data[user_id]:
                user_data[user_id]['portfolio'] = {}
            
            user_data[user_id]['portfolio'][symbol] = {
                'active': True,
                'entry_price': current_price,
                'amount': amount,
                'timestamp': time.time()
            }
            save_settings()
            
            value = amount * current_price
            text = f"""✅ <b>Позиция добавлена!</b>

{symbol}/USDT
💰 Цена входа: ${current_price:,.0f}
🪙 Количество: {amount:.4f}
💵 Сумма: ${value:,.0f}

Теперь бот будет отслеживать вашу позицию в фоновом режиме!
Нажмите «💰 МОЙ ПОРТФЕЛЬ» чтобы увидеть P&L"""
            
            bot.send_message(message.chat.id, text, parse_mode='HTML')
            del user_data[user_id]['temp_symbol']
            save_settings()
        else:
            bot.send_message(message.chat.id, "❌ Ошибка получения цены")

# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    load_settings()
    
    print("=" * 50)
    print("🤖 КРИПТО-ТРЕЙДЕР БОТ v6.0")
    print("=" * 50)
    print("✅ НОВЫЕ ФУНКЦИИ:")
    print("   • Реальный P&L (без привязки к $100)")
    print("   • Фоновое отслеживание цены")
    print("   • Автоматические уведомления")
    print("   • Портфель с реальными позициями")
    print("=" * 50)
    print("✅ БОТ ГОТОВ! Напиши /start в Telegram")
    print("=" * 50)
    
    # Запускаем бота
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
