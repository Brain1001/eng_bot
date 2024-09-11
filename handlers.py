from aiogram import Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import add_word, update_translation, get_word_without_translation, get_user_dictionary, delete_word, word_exists, set_reminder_time
from reminder import schedule_reminders, ReminderStates
import string
import logging
import asyncio
from langdetect import detect  # Импортируем библиотеку для определения языка
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния
class SetReminderTimes(StatesGroup):
    awaiting_morning_time = State()
    awaiting_evening_time = State()

# Определяем состояния
class DeleteWordStates(StatesGroup):
    awaiting_word_for_deletion = State()

# Обработчик команды /start
@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} запустил бота.")
    await message.answer(
        "Приветствую.\n\nЦель этого Телеграм бота -- помочь вам запомнить новые изученные слова. "
        "Для этого он использует научно доказанный подход -- кривую забывания Эббингауза.\n\n"
        "Пожалуйста, укажите примерное время утром в формате: 9:00"
    )
    await state.set_state(SetReminderTimes.awaiting_morning_time)

# Обработчик для получения времени утром
@router.message(SetReminderTimes.awaiting_morning_time)
async def handle_morning_time(message: Message, state: FSMContext):
    time_text = message.text.strip()
    try:
        morning_time = datetime.strptime(time_text, '%H:%M').time()
        await state.update_data(morning_time=morning_time)
        await message.answer("Теперь укажите время вечером в формате: 21:00")
        await state.set_state(SetReminderTimes.awaiting_evening_time)
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, укажите время в формате ЧЧ:ММ (например, 9:00).")

# Обработчик для получения времени вечером
@router.message(SetReminderTimes.awaiting_evening_time)
async def handle_evening_time(message: Message, state: FSMContext):
    user_id = message.from_user.id
    time_text = message.text.strip()
    try:
        evening_time = datetime.strptime(time_text, '%H:%M').time()
        user_data = await state.get_data()
        morning_time = user_data['morning_time']
        set_reminder_time(user_id, morning_time.strftime('%H:%M'), evening_time.strftime('%H:%M'))

        await message.answer(
            f"Напоминания установлены. Утро: {morning_time.strftime('%H:%M')}, Вечер: {evening_time.strftime('%H:%M')}\n"
            "Теперь вы можете отправлять слова, чтобы добавить их в словарь."
        )
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, укажите время в формате ЧЧ:ММ (например, 21:00).")

# Функция для определения языка текста
def detect_language(text):
    try:
        return detect(text)
    except:
        return None

# Обработчик текстовых сообщений от пользователя для добавления слов
@router.message()
async def handle_word(message: Message, state: FSMContext, bot: Bot):
    current_state = await state.get_state()

    if current_state == ReminderStates.awaiting_answer.state:
        await handle_reminder_answer(message, state)
        return

    if current_state == DeleteWordStates.awaiting_word_for_deletion.state:
        await handle_word_deletion(message, state)
        return

    user_id = message.from_user.id
    text = message.text.strip().lower()
    logger.info(f"Получено сообщение от пользователя {user_id}: {text}")

    word = get_word_without_translation(user_id)

    if word:
        update_translation(user_id, word[0], text)
        await update_reminder_list(user_id, word[0], text, state)  # Обновляем список слов

        asyncio.create_task(schedule_reminders(bot, user_id, word[0], text, state))

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Мой словарь", callback_data="show_dictionary")]
            ]
        )
        await message.answer(
            f"Слово *{word[0]}* и его перевод *{text}* добавлены в ваш словарь!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        if word_exists(user_id, text):
            await message.answer("Упс, это слово уже добавлено в словарь.")
            return

        # Добавляем новое слово без проверки языка
        add_word(user_id, text)
        await message.answer(f"Отлично, слово *{text}* добавлено, теперь напишите его перевод!", parse_mode="Markdown")

# Обработчик ответа на напоминание от пользователя
@router.message(ReminderStates.awaiting_answer)
async def handle_reminder_answer(message: Message, state: FSMContext):
    user_data = await state.get_data()
    correct_answers = user_data.get('correct_answers')  # Получаем список правильных переводов

    user_answers = message.text.strip().split("\n")

    if len(user_answers) < len(correct_answers):
        await message.answer("Пожалуйста, ответьте на все вопросы, один ответ на строку.")
        return

    results = []
    for idx, correct_translation in enumerate(correct_answers):
        user_answer = user_answers[idx].strip().lower()

        if user_answer == correct_translation.lower():
            results.append(f"✅ {correct_translation}: правильно!")
        else:
            results.append(f"❌ {correct_translation}: неверно. Правильный перевод: {correct_translation}")

    await message.answer("\n".join(results))

    await state.clear()

# Обновляем список слов для напоминания в состоянии
async def update_reminder_list(user_id: int, word: str, translation: str, state: FSMContext):
    user_data = await state.get_data()
    if 'words_to_remind' not in user_data:
        user_data['words_to_remind'] = []

    if (word, translation) not in user_data['words_to_remind']:
        user_data['words_to_remind'].append((word, translation))
        await state.update_data(words_to_remind=user_data['words_to_remind'])

# Обработчик нажатия на инлайн-кнопку "Мой словарь"
@router.callback_query(lambda c: c.data == 'show_dictionary')
async def show_dictionary(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} запросил свой словарь.")
    
    dictionary = get_user_dictionary(user_id)
    if dictionary:
        dict_text = ""
        for word, translation in dictionary:
            word_lang = detect_language(word)
            translation_lang = detect_language(translation)
            
            # Логика для определения, что является словом, а что переводом:
            # Если слово не на русском языке, выводим его первым, а перевод на русском
            if word_lang != 'ru' and translation_lang == 'ru':
                dict_text += f"{word} - {translation}\n"
            # Если слово на русском, а перевод не на русском, меняем местами
            elif word_lang == 'ru' and translation_lang != 'ru':
                dict_text += f"{translation} - {word}\n"
            # Если оба слова на одном языке или не удается определить язык, выводим как есть
            else:
                dict_text += f"{word} - {translation}\n"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Удалить слово", callback_data="delete_word")]
            ]
        )
        
        await callback_query.message.answer(f"Ваш словарь:\n{dict_text}", reply_markup=keyboard)
    else:
        await callback_query.message.answer("Ваш словарь пуст.")

    await callback_query.answer()


# Обработчик нажатия на инлайн-кнопку "Удалить слово"
@router.callback_query(lambda c: c.data == 'delete_word')
async def ask_for_word_to_delete(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} запросил удаление слова.")
    
    await callback_query.message.answer("Введите слово, которое вы хотите удалить.")
    await state.set_state(DeleteWordStates.awaiting_word_for_deletion)
    
    await callback_query.answer()

# Обработчик для удаления слова после ввода пользователем
@router.message(DeleteWordStates.awaiting_word_for_deletion)
async def handle_word_deletion(message: Message, state: FSMContext):
    user_id = message.from_user.id
    word_to_delete = message.text.strip().lower()
    logger.info(f"Пользователь {user_id} ввел слово для удаления: {word_to_delete}")

    if delete_word(user_id, word_to_delete):
        user_data = await state.get_data()
        if 'words_to_remind' in user_data:
            user_data['words_to_remind'] = [w for w in user_data['words_to_remind'] if w[0] != word_to_delete]
            await state.update_data(words_to_remind=user_data['words_to_remind'])

        await message.answer(f"Слово *{word_to_delete}* удалено.", parse_mode="Markdown")
    else:
        await message.answer(f"Слово *{word_to_delete}* не найдено в вашем словаре.", parse_mode="Markdown")

    await state.clear()
