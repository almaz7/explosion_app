from telebot import types
import database
import config
import markups
import time

bot = config.bot


@bot.callback_query_handler(lambda query: query.data == "curr_sch" or query.data == "edit_sch")
def handle_schedule_options(query: types.CallbackQuery):
    if query.data == "curr_sch":
        print_current_schedule(query.message)
    else:
        bot.send_message(query.message.chat.id, "*Редактирование расписания*", parse_mode='Markdown')
        send_schedule_page(query.message, get_full_schedule())


@bot.callback_query_handler(lambda query: query.data.startswith('set_train:') or query.data.startswith('set_new_time:'))
def set_new_train_handler(query: types.CallbackQuery):
    day_number = int(query.data.split(':')[1])
    bot.send_message(query.message.chat.id, "Установите время тренировки")
    bot.register_next_step_handler(query.message, set_train_time(day_number, query))


@bot.callback_query_handler(lambda query: query.data.startswith('delete_train:'))
def delete_train_time(query: types.CallbackQuery):
    day_number = int(query.data.split(':')[1])
    _, train_time, day_name = get_schedule_day(day_number)

    if train_time is None:
        bot.send_message(query.message.chat.id, "Тренировка на этот день не установлена.")
    else:
        if edit_train_time(day_number, None):
            bot.delete_message(query.message.chat.id, query.message.message_id)
            send_schedule_page(query.message, get_full_schedule(), day_number)


@bot.callback_query_handler(lambda query: query.data.startswith('sch_page:'))
def edit_paging_handler(query: types.CallbackQuery):
    page = int(query.data.split(':')[1])
    bot.delete_message(query.message.chat.id, query.message.message_id)
    send_schedule_page(query.message, get_full_schedule(), page)


def print_current_schedule(message: types.Message):
    train_days = get_current_schedule()

    if len(train_days) > 0:
        message_text = ''

        for day in train_days:
            message_text += f"\n\n{day[2]} {day[1]}"

        bot.send_message(message.chat.id, message_text[2:], reply_markup=markups.main_markup(message))
    else:
        bot.send_message(message.chat.id, "На данный момент расписание не установлено",
                         reply_markup=markups.main_markup(message))


def send_schedule_options(message: types.Message, day):
    train_time = day[1]
    day_name = day[2]
    day_info_text = f"{day_name}\n\nЗанятие не установлено." if train_time is None else f"{day_name} {train_time}"
    bot.send_message(message.chat.id, day_info_text, reply_markup=markups.edit_schedule_options(day))


def send_schedule_page(message: types.Message, schedule, page=1):
    current_day = schedule[page - 1]
    current_day_info = f"{current_day[2]} - {current_day[1]}" if current_day[1] is not None \
        else f"{current_day[2]} - занятие отсутствует."

    bot.send_message(message.chat.id, current_day_info,
                     reply_markup=markups.schedule_paging(page), parse_mode='Markdown')


def set_train_time(day_number: int, query):
    return lambda message: set_train_time_aux(message, day_number, query)


def set_train_time_aux(message: types.Message, day_number: int, query: types.CallbackQuery):
    new_time = message.text
    day = get_schedule_day(day_number)

    if not valid_time(new_time):
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное время тренировки в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, set_train_time(day_number, query))
    else:
        if edit_train_time(day_number, new_time):
            bot.delete_message(query.message.chat.id, query.message.message_id)
            send_schedule_page(query.message, get_full_schedule(), day_number)
        else:
            bot.send_message(message.chat.id, "Номер дня не в рамках [1; 7]")


def get_current_schedule():
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM schedule WHERE train_time IS NOT NULL")
    rows = cursor.fetchall()
    connection.close()

    if len(rows) > 0:
        return rows
    else:
        return []


def get_full_schedule():
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM schedule")
    rows = cursor.fetchall()
    connection.close()

    return rows


def valid_time(time_str: str) -> bool:
    if time_str is None:
        return True

    try:
        time.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False


def edit_train_time(day_number: int, new_time) -> bool:
    if not valid_time(new_time) or not (0 < day_number < 8):
        return False
    else:
        connection = database.getConnection()
        cursor = connection.cursor()
        new_value = "NULL" if new_time is None else f"'{new_time}'"
        cursor.execute(f"UPDATE schedule SET train_time = {new_value} WHERE day_number = {day_number}")
        connection.commit()
        connection.close()
        return True


def get_schedule_day(day_number: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM schedule WHERE day_number = {day_number}")
    day = cursor.fetchone()
    connection.close()

    return day


def get_schedule_weekday_numbers() -> list[int]:
    return [day[0] for day in get_current_schedule()]
