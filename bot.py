import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from config import TOKEN, ADMIN_ID, SPONSORS, PAYMENT_URL, TEXTS
from database import init_db, get_user, update_user

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

PRIZES = {
    1: {"name": "Скидка 10%", "img": "https://via.placeholder.com/400x200?text=Gift+1"},
    2: {"name": "Бесплатная доставка", "img": "https://via.placeholder.com/400x200?text=Gift+2"},
    3: {"name": "Кэшбэк 500р", "img": "https://via.placeholder.com/400x200?text=Gift+3"},
    4: {"name": "Премиум на 1 месяц", "img": "https://via.placeholder.com/400x200?text=Gift+4"},
    5: {"name": "Секретный приз", "img": "https://via.placeholder.com/400x200?text=Gift+5"},
    6: {"name": "Джекпот!", "img": "https://via.placeholder.com/400x200?text=Gift+6"},
}

class BotStates(StatesGroup):
    waiting_for_dice = State()
    sending_screenshots = State()
    waiting_for_subscription = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    
    if user_data and user_data[2] == 'paid':
        await message.answer("Вы уже участвуете в розыгрыше! Ожидайте результатов.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_data="throw_dice")],
        [InlineKeyboardButton(text="📖 Посмотреть отзывы", callback_data="show_reviews")]
    ])
    
    await message.answer_photo(
        photo="https://via.placeholder.com/600x300?text=6+Gifts",
        caption=TEXTS["start"],
        reply_markup=keyboard
    )
    await state.set_state(BotStates.waiting_for_dice)

@dp.callback_query(F.data == "show_reviews")
async def show_reviews(callback: CallbackQuery):
    await callback.answer(TEXTS["reviews"], show_alert=True)

@dp.callback_query(F.data == "throw_dice")
async def throw_dice(callback: CallbackQuery, state: FSMContext):
    dice_msg = await bot.send_dice(callback.message.chat.id, emoji="🎲")
    await asyncio.sleep(4)
    
    dice_value = dice_msg.dice.value
    prize = PRIZES.get(dice_value, PRIZES[1])
    
    await update_user(callback.from_user.id, prize=prize['name'], status='task')
    
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=prize['img'],
        caption=f"🎉 Поздравляем! Твой подарок: *{prize['name']}*\n\n" + TEXTS["task"],
        parse_mode="Markdown"
    )
    
    await state.set_state(BotStates.sending_screenshots)

@dp.message(BotStates.sending_screenshots, F.photo)
async def process_screenshot(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    
    current_count = user_data[1] if user_data else 0
    new_count = current_count + 1
    
    if ADMIN_ID != 0:
        try:
            await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
        except Exception as e:
            print(f"Ошибка пересылки админу: {e}")
    
    await update_user(user_id, screenshots_count=new_count)
    
    if new_count < 10:
        await message.answer(f"✅ Скриншот {new_count}/10 принят. Отправь следующий.")
    else:
        await message.answer("🎉 Все 10 скриншотов приняты! Переходим к следующему шагу.")
        await ask_for_subscription(message, state)

async def ask_for_subscription(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for sponsor in SPONSORS:
        link = f"https://t.me/{sponsor.replace('@', '')}"
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Подписаться на {sponsor}", url=link)])
        
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subs")])
    
    await message.answer(TEXTS["subscribe"], reply_markup=keyboard)
    await state.set_state(BotStates.waiting_for_subscription)

@dp.callback_query(F.data == "check_subs")
async def check_subscriptions(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    not_subscribed = []
    
    for sponsor in SPONSORS:
        try:
            member = await bot.get_chat_member(chat_id=sponsor, user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(sponsor)
        except Exception as e:
            print(f"Ошибка проверки {sponsor}: {e}")
            not_subscribed.append(sponsor)
    
    if not_subscribed:
        await callback.answer(f"❌ Вы не подписаны на: {', '.join(not_subscribed)}", show_alert=True)
    else:
        await update_user(user_id, status='pay')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оформить за 1 ₽", url=PAYMENT_URL)]
        ])
        await callback.message.edit_text(TEXTS["pay"], reply_markup=keyboard)

async def main():
    await init_db()
    print("Giveaway Bot запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
