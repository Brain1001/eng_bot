import asyncio
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta

class ReminderStates(StatesGroup):
    awaiting_answer = State()

# Создаем блокировку для предотвращения параллельных вызовов напоминаний
reminder_lock = asyncio.Lock()

# Функция для отправки сгруппированных напоминаний
async def send_grouped_reminder(bot: Bot, user_id: int, words_and_translations: list, state: FSMContext):
    if not words_and_translations:
        return

    # Формируем сообщение со списком слов
    words_list = "\n".join([f"{idx + 1}. {word}" for idx, (word, _) in enumerate(words_and_translations)])
    message = f"Как переводятся эти слова? Ответьте переводом на каждое слово на отдельной строке:\n{words_list}"

    # Отправляем вопрос пользователю
    await bot.send_message(user_id, message, parse_mode="Markdown")

    # Сохраняем правильные ответы (переводы) в состоянии пользователя
    await state.update_data(correct_answers=[translation for _, translation in words_and_translations])

    # Устанавливаем состояние ожидания ответа пользователя
    await state.set_state(ReminderStates.awaiting_answer)

# Функция для планирования напоминаний
async def schedule_reminders(bot: Bot, user_id: int, word: str, translation: str, state: FSMContext):
    async with reminder_lock:  # Добавляем блокировку для предотвращения повторных вызовов
        user_data = await state.get_data()

        # Получаем утреннее и вечернее время из состояния
        morning_time_str = user_data.get('morning_time')
        evening_time_str = user_data.get('evening_time')

        # Проверяем, установлено ли время
        if not morning_time_str or not evening_time_str:
            # Если время не установлено, используем значения по умолчанию
            morning_time_str = "09:00"
            evening_time_str = "21:00"
            # Можно также отправить сообщение пользователю с просьбой установить время через настройки

        morning_time = datetime.strptime(morning_time_str, '%H:%M').time()
        evening_time = datetime.strptime(evening_time_str, '%H:%M').time()

        now = datetime.now()

        # Добавляем слово и перевод в список для напоминаний
        if 'words_to_remind' not in user_data:
            user_data['words_to_remind'] = []

        if (word, translation) not in user_data['words_to_remind']:
            user_data['words_to_remind'].append((word, translation))
            await state.update_data(words_to_remind=user_data['words_to_remind'])

        # Устанавливаем флаг отправленного напоминания
        if user_data.get('reminder_sent', False):
            return

        # Первое напоминание: сегодня вечером
        first_reminder_time = now.replace(hour=evening_time.hour, minute=evening_time.minute)
        if first_reminder_time < now:
            first_reminder_time += timedelta(days=1)

        await asyncio.sleep((first_reminder_time - now).seconds)
        await send_grouped_reminder(bot, user_id, user_data['words_to_remind'], state)

        # Второе напоминание: на следующее утро
        second_reminder_time = first_reminder_time.replace(hour=morning_time.hour, minute=morning_time.minute) + timedelta(days=1)
        await asyncio.sleep((second_reminder_time - first_reminder_time).seconds)
        await send_grouped_reminder(bot, user_id, user_data['words_to_remind'], state)

        # Третье напоминание: на следующий вечер
        third_reminder_time = second_reminder_time.replace(hour=evening_time.hour, minute=evening_time.minute)
        await asyncio.sleep((third_reminder_time - second_reminder_time).seconds)
        await send_grouped_reminder(bot, user_id, user_data['words_to_remind'], state)

        # Четвертое напоминание: на третий день вечером
        fourth_reminder_time = third_reminder_time + timedelta(days=1)
        await asyncio.sleep((fourth_reminder_time - third_reminder_time).seconds)
        await send_grouped_reminder(bot, user_id, user_data['words_to_remind'], state)

        # Пятое напоминание: на седьмой день вечером
        fifth_reminder_time = third_reminder_time + timedelta(days=5)
        await asyncio.sleep((fifth_reminder_time - fourth_reminder_time).seconds)
        await send_grouped_reminder(bot, user_id, user_data['words_to_remind'], state)

        # Сбрасываем флаг и очищаем список слов после последнего напоминания
        user_data['reminder_sent'] = False
        user_data['words_to_remind'] = []
        await state.update_data(user_data)
