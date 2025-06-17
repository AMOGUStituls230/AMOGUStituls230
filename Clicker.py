import os
import json
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Конфигурация
TOKEN = os.environ.get('TELEGRAM_API_KEY')
USER_DATA_FILE = "user_data.json"
CHANNEL_USERNAME = "@ClickerBa"  # Имя канала для подписки
BOT_USERNAME = "UsetAirdropOnly_Bot"  # ЗАМЕНИТЕ НА РЕАЛЬНОЕ ИМЯ БОТА

# Загрузка данных пользователей
def load_user_data():
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Сохранение данных пользователей
def save_user_data(user_data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=2)

# Инициализация данных пользователя с защитой от отсутствующих ключей
def init_user_data(user_id):
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    # Стандартная структура данных
    default_data = {
        'money': 0,
        'click_level': 0,
        'rebirth_level': 0,
        'click_upgrade_cost': 100,
        'rebirth_cost': 5000,
        'subscribed': False,
        'referrals': 0,
        'active_referrals': 0,
        'last_click_time': 0,
        'referrer': None
    }
    
    if user_id_str not in user_data:
        user_data[user_id_str] = default_data
        save_user_data(user_data)
        return user_data[user_id_str]
    
    # Добавляем отсутствующие ключи
    current_data = user_data[user_id_str]
    for key in default_data:
        if key not in current_data:
            current_data[key] = default_data[key]
    
    save_user_data(user_data)
    return current_data

# Обновление данных пользователя
def update_user_data(user_id, data):
    user_data = load_user_data()
    user_data[str(user_id)] = data
    save_user_data(user_data)

# Расчет силы клика
def calculate_click_power(user_data):
    return 1 + user_data['click_level'] * (2 ** user_data['rebirth_level'])

# Основная клавиатура (Inline)
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Баланс", callback_data='balance'),
         InlineKeyboardButton("⚡ Клик", callback_data='click')],
        [InlineKeyboardButton("🛠 Апгрейды", callback_data='upgrades'),
         InlineKeyboardButton("🔥 Rebirth", callback_data='rebirth_info')],
        [InlineKeyboardButton("🫂 Рефералы 🫂", callback_data='referrals')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Reply-клавиатура (постоянная под строкой ввода)
def get_reply_keyboard():
    return ReplyKeyboardMarkup(
        [["💰 Баланс", "⚡ Клик"], 
         ["🛠 Апгрейды", "🔥 Rebirth"],
         ["🫂 Рефералы 🫂"]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# Клавиатура для проверки подписки
def subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Я подписался", callback_data='check_subscription')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура улучшений
def upgrades_keyboard(user_data):
    keyboard = [
        [InlineKeyboardButton(
            f"⚙️ +1 клик (Ур. {user_data['click_level']}) - {user_data['click_upgrade_cost']}$", 
            callback_data='buy_click_upgrade')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура ребитха
def rebirth_keyboard(user_data):
    keyboard = [
        [InlineKeyboardButton(
            f"🔥 Rebirth (Ур. {user_data['rebirth_level']}) - {user_data['rebirth_cost']}$", 
            callback_data='do_rebirth')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура рефералов
def referrals_keyboard(user_id, user_data):
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    keyboard = [
        [InlineKeyboardButton("📢 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся%20к%20моей%20игре%20кликер!")],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Проверка подписки на канал
async def check_channel_subscription(user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, 
            user_id=user_id
        )
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = init_user_data(user_id)
    
    # Обработка реферальных ссылок
    if context.args:
        for arg in context.args:
            if arg.startswith('ref_'):
                try:
                    referrer_id = int(arg[4:])
                    # Проверяем, что пользователь еще не имеет реферера
                    if user_data.get('referrer') is None:
                        # Проверяем, что реферер существует
                        all_data = load_user_data()
                        if str(referrer_id) in all_data:
                            user_data['referrer'] = referrer_id
                            # Обновляем данные реферера
                            referrer_data = all_data[str(referrer_id)]
                            referrer_data['referrals'] = referrer_data.get('referrals', 0) + 1
                            update_user_data(referrer_id, referrer_data)
                except ValueError:
                    pass
    
    is_subscribed = await check_channel_subscription(user_id, context)
    user_data['subscribed'] = is_subscribed
    
    # Обновляем статус у реферера, если пользователь подписан
    if user_data.get('referrer') and is_subscribed:
        referrer_id = user_data['referrer']
        all_data = load_user_data()
        if str(referrer_id) in all_data:
            referrer_data = all_data[str(referrer_id)]
            referrer_data['active_referrals'] = referrer_data.get('active_referrals', 0) + 1
            update_user_data(referrer_id, referrer_data)
    
    update_user_data(user_id, user_data)
    
    if not is_subscribed:
        welcome_text = (
            "🎮 Добро пожаловать в Clicker Game!\n\n"
            "❌ Для игры необходимо подписаться на наш канал:\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            "После подписки нажмите кнопку ✅ Я подписался"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=subscription_keyboard()
        )
    else:
        welcome_text = (
            "🎮 Добро пожаловать в Clicker Game!\n\n"
            "✅ Вы подписаны на канал! Можете начинать игру.\n\n"
            "Используйте кнопки ниже для игры:"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_reply_keyboard()
        )

# Обработчик текстовых команд
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id
    user_data = init_user_data(user_id)
    
    # Проверяем подписку
    if not user_data.get('subscribed', False):
        await update.message.reply_text(
            "❌ Для игры необходимо подписаться на канал!",
            reply_markup=subscription_keyboard()
        )
        return
    
    if text == "💰 Баланс":
        await show_balance(update, context)
    elif text == "⚡ Клик":
        await handle_click(update, context)
    elif text == "🛠 Апгрейды":
        await show_upgrades(update, context)
    elif text == "🔥 Rebirth":
        await rebirth_info(update, context)
    elif text == "🫂 Рефералы 🫂":
        await show_referrals(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки для управления игрой",
            reply_markup=get_reply_keyboard()
        )

# Обработчик проверки подписки
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = init_user_data(user_id)
    
    is_subscribed = await check_channel_subscription(user_id, context)
    
    if is_subscribed:
        user_data['subscribed'] = True
        
        # Обновляем статус у реферера
        if user_data.get('referrer'):
            referrer_id = user_data['referrer']
            all_data = load_user_data()
            if str(referrer_id) in all_data:
                referrer_data = all_data[str(referrer_id)]
                referrer_data['active_referrals'] = referrer_data.get('active_referrals', 0) + 1
                update_user_data(referrer_id, referrer_data)
        
        update_user_data(user_id, user_data)
        
        await query.edit_message_text(
            text="✅ Спасибо за подписку! Теперь вы можете играть."
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Используйте кнопки ниже для игры:",
            reply_markup=get_reply_keyboard()
        )
    else:
        await query.answer("❌ Вы ещё не подписались на канал! Пожалуйста, подпишитесь и попробуйте снова.", show_alert=True)

# Обработчик кнопки баланса
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем тип обновления (callback или message)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        is_callback = True
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        is_callback = False
    
    user_data = init_user_data(user_id)
    click_power = calculate_click_power(user_data)
    
    balance_text = (
        f"💰 Ваш баланс: {user_data.get('money', 0)}$\n"
        f"⚡ Сила клика: {click_power}\n"
        f"🛠 Уровень клика: {user_data.get('click_level', 0)}\n"
        f"🔥 Уровень Rebirth: {user_data.get('rebirth_level', 0)}\n"
        f"Статус подписки: {'✅ Подписан' if user_data.get('subscribed', False) else '❌ Не подписан'}\n\n"
        f"👥 Рефералы: {user_data.get('referrals', 0)} (Активных: {user_data.get('active_referrals', 0)})"
    )
    
    if is_callback:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=balance_text,
            reply_markup=main_keyboard()
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=balance_text,
            reply_markup=main_keyboard()
        )

# Обработчик клика
async def handle_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем тип обновления
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        is_callback = True
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        is_callback = False
    
    user_data = init_user_data(user_id)
    
    # Проверяем подписку
    if not user_data.get('subscribed', False):
        if is_callback:
            await query.answer("❌ Для клика необходимо подписаться на канал!", show_alert=True)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Для клика необходимо подписаться на канал!",
                reply_markup=subscription_keyboard()
            )
        return
    
    # Анти-автокликер: случайная задержка от 0.5 до 1.4 секунд
    current_time = time.time()
    last_click_time = user_data.get('last_click_time', 0)
    time_since_last_click = current_time - last_click_time
    min_delay = 0.5
    max_delay = 1.4
    required_delay = random.uniform(min_delay, max_delay)
    
    if time_since_last_click < required_delay:
        remaining = round(required_delay - time_since_last_click, 1)
        if is_callback:
            await query.answer(f"⏳ Кликайте медленнее! Подождите {remaining} сек.", show_alert=True)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏳ Кликайте медленнее! Подождите {remaining} сек.",
            )
        return
    
    # Обновляем время последнего клика
    user_data['last_click_time'] = current_time
    
    # Добавляем деньги
    click_power = calculate_click_power(user_data)
    user_data['money'] = user_data.get('money', 0) + click_power
    
    # Начисляем бонус рефереру (20%)
    referrer_id = user_data.get('referrer')
    if referrer_id:
        all_data = load_user_data()
        if str(referrer_id) in all_data:
            referrer_data = all_data[str(referrer_id)]
            bonus = round(click_power * 0.2)
            if bonus < 1:
                bonus = 1
            referrer_data['money'] = referrer_data.get('money', 0) + bonus
            update_user_data(referrer_id, referrer_data)
    
    update_user_data(user_id, user_data)
    
    result_text = f"✅ +{click_power}$! Ваш баланс: {user_data['money']}$"
    
    if is_callback:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text,
            reply_markup=main_keyboard()
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=result_text,
            reply_markup=main_keyboard()
        )

# Обработчик рефералов
async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем тип обновления
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        is_callback = True
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        is_callback = False
    
    user_data = init_user_data(user_id)
    
    # Создаем реферальную ссылку
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    referrals_text = (
        f"👥 Реферальная система:\n\n"
        f"🔗 Ваша реферальная ссылка:\n{ref_link}\n\n"
        f"📊 Ваша статистика:\n"
        f"• Всего приглашено: {user_data.get('referrals', 0)}\n"
        f"• Активных рефералов: {user_data.get('active_referrals', 0)}\n\n"
        f"💸 Бонусная система:\n"
        f"• За каждого активного реферала вы получаете 20% от его кликов!\n"
        f"• Реферал считается активным, если он подписан на канал\n\n"
        f"Поделитесь ссылкой с друзьями и получайте пассивный доход!"
    )
    
    if is_callback:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=referrals_text,
            reply_markup=referrals_keyboard(user_id, user_data)
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=referrals_text,
            reply_markup=referrals_keyboard(user_id, user_data))
        

# Обработчик апгрейдов
async def show_upgrades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем тип обновления
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        is_callback = True
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        is_callback = False
    
    user_data = init_user_data(user_id)
    
    # Проверяем подписку
    if not user_data.get('subscribed', False):
        if is_callback:
            await query.answer("❌ Для улучшений необходимо подписаться на канал!", show_alert=True)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Для улучшений необходимо подписаться на канал!",
                reply_markup=subscription_keyboard()
            )
        return
    
    upgrades_text = (
        f"🛠 Улучшения:\n\n"
        f"💰 Ваш баланс: {user_data.get('money', 0)}$\n"
        f"⚡ Сила клика: {calculate_click_power(user_data)}\n"
        f"🛠 Уровень клика: {user_data.get('click_level', 0)}\n"
        f"🔥 Уровень Rebirth: {user_data.get('rebirth_level', 0)}\n\n"
        f"Выберите улучшение:"
    )
    
    if is_callback:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=upgrades_text,
            reply_markup=upgrades_keyboard(user_data)
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=upgrades_text,
            reply_markup=upgrades_keyboard(user_data)
        )

# Обработчик покупки улучшения клика
async def buy_click_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = init_user_data(user_id)
    
    # Проверяем подписку
    if not user_data.get('subscribed', False):
        await query.answer("❌ Для покупки улучшений необходимо подписаться на канал!", show_alert=True)
        return
    
    if user_data.get('money', 0) >= user_data.get('click_upgrade_cost', 100):
        user_data['money'] = user_data.get('money', 0) - user_data.get('click_upgrade_cost', 100)
        user_data['click_level'] = user_data.get('click_level', 0) + 1
        user_data['click_upgrade_cost'] = user_data.get('click_upgrade_cost', 100) * 3
        update_user_data(user_id, user_data)
        
        result_text = (
            f"✅ Улучшение куплено!\n\n"
            f"⚡ Новый уровень клика: {user_data.get('click_level', 0)}\n"
            f"💪 Сила клика: {calculate_click_power(user_data)}\n"
            f"💰 Остаток: {user_data.get('money', 0)}$"
        )
    else:
        result_text = f"❌ Недостаточно денег! Нужно {user_data.get('click_upgrade_cost', 100)}$"
    
    await query.edit_message_text(
        text=result_text,
        reply_markup=upgrades_keyboard(user_data)
    )

# Обработчик информации о ребитхе
async def rebirth_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем тип обновления
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        is_callback = True
    else:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        is_callback = False
    
    user_data = init_user_data(user_id)
    
    # Проверяем подписку
    if not user_data.get('subscribed', False):
        if is_callback:
            await query.answer("❌ Для ребитха необходимо подписаться на канал!", show_alert=True)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Для ребитха необходимо подписаться на канал!",
                reply_markup=subscription_keyboard()
            )
        return
    
    # Рассчитаем силу клика после ребитха
    after_rebirth_power = 1 * (2 ** (user_data.get('rebirth_level', 0) + 1))
    current_power = calculate_click_power(user_data)
    
    rebirth_text = (
        "🔥 Rebirth:\n\n"
        "После Rebirth:\n"
        "- Ваши деньги обнулятся\n"
        "- Улучшения клика сбросятся\n"
        "- Вы получите +100% к силе клика\n\n"
        f"Текущий уровень: {user_data.get('rebirth_level', 0)}\n"
        f"Стоимость: {user_data.get('rebirth_cost', 1000)}$\n\n"
        f"После Rebirth ваша сила клика будет:\n"
        f"⚡ {after_rebirth_power} вместо текущих {current_power}"
    )
    
    if is_callback:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=rebirth_text,
            reply_markup=rebirth_keyboard(user_data)
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=rebirth_text,
            reply_markup=rebirth_keyboard(user_data)
        )

# Обработчик выполнения ребитха
async def do_rebirth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = init_user_data(user_id)
    
    # Проверяем подписку
    if not user_data.get('subscribed', False):
        await query.answer("❌ Для ребитха необходимо подписаться на канал!", show_alert=True)
        return
    
    if user_data.get('money', 0) >= user_data.get('rebirth_cost', 1000):
        # Сохраняем старые значения для сообщения
        old_level = user_data.get('rebirth_level', 0)
        
        # Выполняем ребитх
        user_data['money'] = 0
        user_data['click_level'] = 0
        user_data['rebirth_level'] = old_level + 1
        user_data['click_upgrade_cost'] = 100
        user_data['rebirth_cost'] = user_data.get('rebirth_cost', 1000) * 10
        update_user_data(user_id, user_data)
        
        new_power = calculate_click_power(user_data)
        
        result_text = (
            f"🔥 Rebirth выполнен!\n\n"
            f"🎉 Новый уровень Rebirth: {user_data.get('rebirth_level', 0)} (был {old_level})\n"
            f"⚡ Ваша новая сила клика: {new_power}\n"
            f"💰 Ваш баланс: {user_data.get('money', 0)}$"
        )
    else:
        result_text = f"❌ Недостаточно денег! Нужно {user_data.get('rebirth_cost', 1000)}$"
    
    await query.edit_message_text(
        text=result_text,
        reply_markup=rebirth_keyboard(user_data)
    )

# Возврат в главное меню
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = init_user_data(user_id)
    click_power = calculate_click_power(user_data)
    
    await query.edit_message_text(
        text=f"💰 Баланс: {user_data.get('money', 0)}$ | ⚡ Сила клика: {click_power}",
        reply_markup=main_keyboard()
    )

# Основная функция
def main() -> None:
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    
    # Регистрация обработчиков текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Регистрация обработчиков callback-запросов
    application.add_handler(CallbackQueryHandler(check_subscription, pattern='^check_subscription$'))
    application.add_handler(CallbackQueryHandler(show_balance, pattern='^balance$'))
    application.add_handler(CallbackQueryHandler(handle_click, pattern='^click$'))
    application.add_handler(CallbackQueryHandler(show_upgrades, pattern='^upgrades$'))
    application.add_handler(CallbackQueryHandler(rebirth_info, pattern='^rebirth_info$'))
    application.add_handler(CallbackQueryHandler(do_rebirth, pattern='^do_rebirth$'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back$'))
    application.add_handler(CallbackQueryHandler(show_referrals, pattern='^referrals$'))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
