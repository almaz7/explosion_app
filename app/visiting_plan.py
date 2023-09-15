from telebot import types
import telebot
import config
import database
import datetime

import feedbacks
import markups
import train_schedule
import users

bot = config.bot


@bot.callback_query_handler(lambda query: query.data.startswith('sch_filling:'))
def train_plan_page_callback(query: types.CallbackQuery):
    try:
        page = int(query.data.split(':')[1])
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return
    blank_dates = get_user_blank_days(query.message.chat.id,
                                      convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers()))

    bot.delete_message(query.message.chat.id, query.message.message_id)
    send_plan_paging(query.message.chat.id, blank_dates, page)


@bot.callback_query_handler(lambda query: query.data.startswith('sch_editing:'))
def train_plan_edit_page_callback(query: types.CallbackQuery):
    try:
        page = int(query.data.split(':')[1])
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return

    train_dates_to_edit = convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers())
    bot.delete_message(query.message.chat.id, query.message.message_id)
    send_plan_edit_paging(query.message.chat.id, train_dates_to_edit, page)


@bot.callback_query_handler(lambda query: query.data.startswith('will_come:') or query.data.startswith('will_late:'))
def will_come_handler(query: types.CallbackQuery):
    date = query.data.split(':')[1]
    answer = 0 if query.data.startswith('will_come') else 1

    insert_visit_plan_row(query.message.chat.id, date, answer=answer)
    train_dates_to_fill = get_user_blank_days(query.message.chat.id,
                                              convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers()))
    bot.delete_message(query.message.chat.id, query.message.message_id)
    send_plan_paging(query.message.chat.id, train_dates_to_fill)


@bot.callback_query_handler(lambda query: query.data.startswith('will_come_edit:') or
                                          query.data.startswith('will_late_edit:'))
def will_come_edit_handler(query: types.CallbackQuery):
    try:
        date = query.data.split(':')[1]
        page = int(query.data.split(':')[2])
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return

    answer = 0 if query.data.startswith('will_come') else 1
    train_dates_to_fill = convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers())

    if not get_plan_for_day(query.message.chat.id, date):
        insert_visit_plan_row(query.message.chat.id, date, answer=answer)
    else:
        update_visit_plan_row(query.message.chat.id, date, answer=answer, skip_reason=None)

    bot.delete_message(query.message.chat.id, query.message.message_id)
    send_plan_edit_paging(query.message.chat.id, train_dates_to_fill, page)


@bot.callback_query_handler(lambda query: query.data == 'curr_visit_plan')
def curr_visit_plan_handler(query: types.CallbackQuery):
    get_my_current_plan(query.message)


@bot.callback_query_handler(lambda query: query.data == 'edit_visit_plan')
def edit_visit_plan_handler(query: types.CallbackQuery):
    train_dates_to_edit = convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers())
    send_plan_edit_paging(query.message.chat.id, train_dates_to_edit)


@bot.callback_query_handler(lambda query: query.data.startswith('change_skip_reason:'))
def change_skip_reason_handler(query: types.CallbackQuery):
    try:
        date = query.data.split(':')[1]
        page = int(query.data.split(':')[2])
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return

    bot.send_message(query.message.chat.id, "Укажите причину пропуска.")
    bot.register_next_step_handler(query.message, register_skip_reason(date, query, True, page))


@bot.callback_query_handler(lambda query: query.data.startswith('will_not_come:') or
                                          query.data.startswith('will_not_come_edit:'))
def will_not_come_handler(query: types.CallbackQuery):
    try:
        date = query.data.split(':')[1]
        page = int(query.data.split(':')[2])
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return

    is_editing = query.data.startswith('will_not_come_edit:')

    bot.send_message(query.message.chat.id, "Укажите причину пропуска.")
    bot.register_next_step_handler(query.message, register_skip_reason(date, query, is_editing, page))


def register_skip_reason(date: str, query, is_editing: bool, page: int):
    return lambda message: register_skip_reason_aux(message, date, query, is_editing, page)


def register_skip_reason_aux(message: types.Message, date: str, query: types.CallbackQuery, is_editing: bool,
                             page: int):
    skip_reason = message.text

    if skip_reason is None and message.caption is None:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте сообщение, содержащее текст")
        bot.register_next_step_handler(message, register_skip_reason(date, query, is_editing, page))
        return
    elif message.caption is not None:
        skip_reason = message.caption
        bot.send_message(message.chat.id, "Внимание! Прикрепленный вами файл не будет виден администраторам!")

    if is_editing:
        if not get_plan_for_day(message.chat.id, date):
            insert_visit_plan_row(message.chat.id, date, answer=2, skip_reason=skip_reason)
        else:
            update_visit_plan_row(message.chat.id, date, answer=2, skip_reason=skip_reason)

        train_dates_to_fill = convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers())
        bot.delete_message(message.chat.id, query.message.message_id)
        send_plan_edit_paging(message.chat.id, train_dates_to_fill, page)
    else:
        insert_visit_plan_row(message.chat.id, date, answer=2, skip_reason=skip_reason)
        train_dates_to_fill = get_user_blank_days(message.chat.id,
                                                  convert_weekdays_to_dates(
                                                      train_schedule.get_schedule_weekday_numbers()))
        bot.delete_message(message.chat.id, query.message.message_id)
        send_plan_paging(message.chat.id, train_dates_to_fill)


def send_filling_train_plan():
    active_users = users.get_active_users()
    train_days = train_schedule.get_current_schedule()
    if len(train_days) == 0:
        feedbacks.send_notification_to_admins(False, "*Вы не установили расписание!!!*")
        return

    for user in active_users:
        user_id = user[0]
        dates_to_fill = convert_weekdays_to_dates([train_day[0] for train_day in train_days])
        try:
            send_plan_paging(user_id, get_user_blank_days(user_id, dates_to_fill))
        except telebot.apihelper.ApiTelegramException:
            continue


def send_plan_paging(user_id: int, train_dates_to_fill: list[datetime.date], page: int = 1):
    if not train_dates_to_fill:
        bot.send_message(user_id, "Вы заполнили все тренировки.")
        return

    date = train_dates_to_fill[page - 1]
    day_number = date.weekday() + 1
    day = train_schedule.get_schedule_day(day_number)
    message_text = f"{day[2]} ({date.strftime('%d.%m.%Y')}) - {day[1]}"

    bot.send_message(user_id, message_text, reply_markup=markups.train_schedule_filling(train_dates_to_fill, page))


def send_plan_edit_paging(user_id: int, train_dates_to_edit: list[datetime.date], page: int = 1):
    if not train_dates_to_edit:
        bot.send_message(user_id, "Вам нечего редактировать.")
        return

    date = train_dates_to_edit[page - 1]
    current_day_plan = get_plan_for_day(user_id, date.strftime('%d-%m-%Y'))
    day = train_schedule.get_schedule_day(date.weekday() + 1)
    message_text = ''

    if current_day_plan:
        skip_reason = None
        if current_day_plan[4] == 2:
            skip_reason = current_day_plan[5]

        skip_reason_str = f'\n*Причина пропуска*: {skip_reason}' if skip_reason is not None else ''
        message_text = f"*{day[2]} ({date.strftime('%d.%m.%Y')}) {day[1]}*" \
                       f"\n*Текущий ответ*: {answer_to_str(current_day_plan[4])}" \
                       f"{skip_reason_str}"
    else:
        message_text = f"*{day[2]} ({date.strftime('%d.%m.%Y')}) {day[1]}*" \
                       f"\n*Текущий ответ*: не заполнено"

    bot.send_message(user_id, message_text,
                     reply_markup=markups.train_schedule_editing(user_id, train_dates_to_edit, page),
                     parse_mode='Markdown')


def convert_weekdays_to_dates(weekday_numbers: list[int]) -> list[datetime.date]:
    if len(weekday_numbers) > 0:
        result = []
        current_date = datetime.datetime.today().date()
        current_weekday_number = current_date.weekday() + 1
        day_deltas = [wd_number - current_weekday_number for wd_number in weekday_numbers]
        not_negative_day_deltas = [delta for delta in day_deltas if delta >= 0]

        if not_negative_day_deltas:
            for day_delta in not_negative_day_deltas:
                day_date = current_date + datetime.timedelta(days=day_delta)
                result.append(day_date)
        else:
            for day_delta in day_deltas:
                day_date = current_date + datetime.timedelta(days=day_delta + 7)
                result.append(day_date)
        return result
    else:
        print("weekday_numbers is empty!")
        return []


def get_my_current_plan(message: types.Message):
    train_dates = convert_weekdays_to_dates(train_schedule.get_schedule_weekday_numbers())
    user_id = message.chat.id
    plan_info_message = 'Мой план тренировок на неделю.'

    for date in train_dates:
        date_plan = get_plan_for_day(user_id, date.strftime("%d-%m-%Y"))
        train_weekday = train_schedule.get_schedule_day(date.weekday() + 1)

        if date_plan:
            answer = answer_to_str(date_plan[4])
            skip_reason = None

            if date_plan[4] == 2:
                skip_reason = date_plan[5]

            skip_reason_str = '\n*Причина пропуска*: ' + skip_reason if skip_reason is not None else ''
            plan_info_message += f"\n\n*{train_weekday[2]}* ({date.strftime('%d.%m.%Y')}) *{train_weekday[1]}*: " \
                                 f"\n*Ответ*: {answer} " \
                                 f"{skip_reason_str}"
        else:
            plan_info_message += f"\n\n*{train_weekday[2]}* ({date.strftime('%d.%m.%Y')}) *{train_weekday[1]}*: " \
                                 f"\nНе заполнено"

    bot.send_message(user_id, plan_info_message, reply_markup=markups.main_markup(message), parse_mode='Markdown')


def get_user_blank_days(user_id: int, dates_to_fill: list[datetime.date]) -> list[datetime.date]:
    user_visits = get_user_visits(user_id)
    seen = set()
    user_visits = [x for x in user_visits if x not in seen and not seen.add(x)]  # distinct with order saving

    if user_visits:
        result = []

        for date in dates_to_fill:
            date_str = date.strftime("%d-%m-%Y")
            if date_str not in user_visits:
                result.append(date)

        return result
    else:
        return dates_to_fill


def get_plan_for_day(user_id: int, train_date: str):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM visit_plan WHERE user_id = {user_id} "
                   f"AND train_date = '{train_date}'")
    rows = cursor.fetchall()
    connection.close()

    if rows:
        return rows[0]
    else:
        return []


def get_user_visits(user_id: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT train_date FROM visit_plan WHERE user_id = {user_id}")
    rows = cursor.fetchall()
    connection.close()

    if rows:
        return [row[0] for row in rows]
    else:
        return []


def insert_visit_plan_row(user_id: int, date_str: str, answer: int, skip_reason=None):
    timestamp = datetime.datetime.today().strftime("%d-%m-%Y %H:%M:%S")

    connection = database.getConnection()
    cursor = connection.cursor()
    insert_row = f"INSERT INTO visit_plan (user_id, timestamp, train_date, answer, skip_reason) " \
                 f"VALUES ({user_id}, '{timestamp}', '{date_str}', {answer}, '{skip_reason}')"
    cursor.execute(insert_row)
    connection.commit()
    connection.close()


def update_visit_plan_row(user_id: int, date_str: str, answer: int, skip_reason=None):
    connection = database.getConnection()
    cursor = connection.cursor()
    update_row = f"UPDATE visit_plan SET answer = {answer}, skip_reason = '{skip_reason}' " \
                 f"WHERE user_id = {user_id} AND train_date = '{date_str}'"
    cursor.execute(update_row)
    connection.commit()
    connection.close()


def answer_to_str(int_answer: int) -> str:
    if int_answer == 0:
        return "Приду."
    elif int_answer == 1:
        return "Приду, но опоздаю."
    else:
        return "Не приду."
