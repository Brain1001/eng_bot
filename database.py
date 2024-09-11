import sqlite3

# Функция для подключения к базе данных и создания таблицы, если её нет
def init_db():
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_words (
            user_id INTEGER,
            word TEXT,
            translation TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            morning_time TEXT,
            evening_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Функция для добавления слова в базу данных
def add_word(user_id, word):
    word = word.lower()  # Приводим слово к нижнему регистру
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_words (user_id, word, translation) VALUES (?, ?, ?)', (user_id, word, None))
    conn.commit()
    conn.close()

# Функция для проверки, существует ли слово в базе данных
def word_exists(user_id, word):
    word = word.lower()  # Приводим слово к нижнему регистру
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM user_words WHERE user_id = ? AND word = ?', (user_id, word))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Функция для обновления перевода слова в базе данных
def update_translation(user_id, word, translation):
    word = word.lower()  # Приводим слово к нижнему регистру
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE user_words SET translation = ? WHERE user_id = ? AND word = ?', (translation, user_id, word))
    conn.commit()
    conn.close()

# Функция для получения слова без перевода из базы данных
def get_word_without_translation(user_id):
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM user_words WHERE user_id = ? AND translation IS NULL', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Функция для получения словаря пользователя
def get_user_dictionary(user_id):
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('SELECT word, translation FROM user_words WHERE user_id = ?', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

# Функция для удаления слова из базы данных
def delete_word(user_id, word):
    word = word.lower()  # Приводим слово к нижнему регистру
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_words WHERE user_id = ? AND word = ?', (user_id, word))
    deleted = cursor.rowcount > 0  # Возвращает True, если слово было удалено
    conn.commit()
    conn.close()
    return deleted

# Функции для работы с временем напоминаний
def set_reminder_time(user_id, morning_time, evening_time):
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO user_settings (user_id, morning_time, evening_time) VALUES (?, ?, ?)', (user_id, morning_time, evening_time))
    conn.commit()
    conn.close()

def get_reminder_times(user_id):
    conn = sqlite3.connect('user_dictionary.db')
    cursor = conn.cursor()
    cursor.execute('SELECT morning_time, evening_time FROM user_settings WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result
