import telebot
from telebot import types
import config
import database
import datetime

import markups
import string_constants
import train_schedule
import users

bot = config.bot


def note_people(message: types.Message):
    train_days = train_schedule.get_current_schedule()
    current_date = datetime.datetime.today().date()
    current_weekday_number = current_date.weekday() + 1
    for train_day in train_days:
        if current_weekday_number == train_day[0]:
            bot.send_message(message.chat.id, "Сегодня день тренировки")
            send_list_of_people(message, current_date.strftime("%d-%m-%Y"))
            return
    bot.send_message(message.chat.id, "Сегодня тренировки не запланировано")


def send_list_of_people(message: types.Message, date: str):
    active_users = users.get_active_users()
    note_status = False
    for user in active_users:
        user_id = user[0]
        if not check_note_already(user_id, date):
            note_status = True
            firstname = user[1]
            lastname = user[2]
            markup = markups.choose_fact_visiting(user_id, date)
            bot.send_message(message.chat.id, lastname + " " + firstname, reply_markup=markup)
    if not note_status:
        bot.send_message(message.chat.id, "Все уже отмечены")
    markup_new = markups.change_or_look_fact_visiting(date)
    bot.send_message(message.chat.id, "Изменить или посмотреть факт посещений", reply_markup=markup_new)


@bot.callback_query_handler(lambda query: query.data.startswith('is_here:') or query.data.startswith('not_here:'))
def query_fact_visiting(query: types.CallbackQuery):
    try:
        user_id = int(query.data.split(':')[1])
        date = query.data.split(':')[2]
        change_status = int(query.data.split(':')[3])
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return

    answer = 0 if query.data.startswith('is_here') else 1
    if date == datetime.datetime.today().date().strftime("%d-%m-%Y"):
        if not check_note_already(user_id, date):
            insert_visit_fact_row(user_id, date, answer)
        elif change_status == 0:
            bot.send_message(query.message.chat.id, "Данный человек уже отмечен")
        elif change_status == 1:
            update_visit_fact_row(user_id, date, answer)
    else:
        bot.send_message(query.message.chat.id, "Время вышло, отмечать людей за этот день уже нельзя(")
    bot.delete_message(query.message.chat.id, query.message.message_id)


@bot.callback_query_handler(lambda query: query.data.startswith('change_fact:') or query.data.startswith('look_fact:'))
def query_change_look_fact_visiting(query: types.CallbackQuery):
    date = query.data.split(':')[1]
    if query.data.startswith('change_fact:'):
        change_visit_fact(date, query.message)
    else:
        if not compare_people_count(users.get_active_users(), get_visit_fact_row(date)):
            bot.send_message(query.message.chat.id, "Не все люди отмечены. Не ленитесь, сделайте свою работу 😉")
        result_str = show_visit_fact(date)
        bot.send_message(query.message.chat.id, result_str)


@bot.callback_query_handler(lambda query: query.data.startswith('change_visit_fact:'))
def query_change_visit_fact(query: types.CallbackQuery):
    try:
        user_id = int(query.data.split(':')[1])
        date = query.data.split(':')[2]
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")
        return

    row = get_fact_by_date_and_id(user_id, date)
    user = users.get_user(user_id)
    firstname = user[1]
    lastname = user[2]
    string = lastname + " " + firstname + ":\nТекущий статус: "
    if not row:          #не отмечен
        string += "Не отмечен "
        markup = markups.choose_fact_visiting(user_id, date, 0)
    elif row[0] == 0:
        string += string_constants.IS_HERE
        markup = markups.choose_fact_visiting(user_id, date, 1)
    elif row[0] == 1:
        string += string_constants.NOT_HERE
        markup = markups.choose_fact_visiting(user_id, date, 1)
    string += "\nВыберите новый статус:\n"
    bot.send_message(query.message.chat.id, string, reply_markup=markup)
    bot.delete_message(query.message.chat.id, query.message.message_id)


def change_visit_fact(date: str, message: types.Message):
    active_users = users.get_active_users()
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    for user in active_users:
        user_id = user[0]
        firstname = user[1]
        lastname = user[2]
        markup.add(
            types.InlineKeyboardButton(lastname + " " + firstname, callback_data=f"change_visit_fact:{user_id}:{date}"),
        )
    bot.send_message(message.chat.id, "Выберите, чей факт посещений хотите изменить", reply_markup=markup)


def compare_people_count(row1, row2):
    count1 = 0
    count2 = 0
    for people in row1:
        count1 += 1
    for people in row2:
        count2 += 1
    if count1 == count2:
        return True
    else:
        return False


def show_visit_fact(date: str):
    fact_rows = get_visit_fact_row(date)

    result = "Отчет по сегодняшней тренировке " + date + ":\n"
    num = 0
    for fact_row in fact_rows:
        num += 1
        user_id = fact_row[0]
        firstname = fact_row[1]
        lastname = fact_row[2]
        fact_answer = fact_row[3]
        plan_row = get_plan_answer_by_date_and_id(user_id, date)

        if plan_row:
            plan_answer = plan_row[0]
            skip_reason = plan_row[1]
        else:
            plan_answer = -1  #Не отмечен в плане

        result += str(num) + ". " + lastname + " " + firstname + ": "

        if fact_answer == 0:
            result += string_constants.IS_HERE + "\n"
        else:
            result += string_constants.NOT_HERE + "\n"

        result += "План: "
        if plan_answer == -1:
            result += "Не отмечен" + "\n"
        elif plan_answer == 0:
            result += string_constants.WILL_COME + "\n"
        elif plan_answer == 1:
            result += string_constants.WILL_LATE + "\n"
        elif plan_answer == 2:
            result += string_constants.WILL_NOT_COME + "\n"
            result += "Причина пропуска: " + skip_reason + "\n"
        result += "\n"
    return result


def check_note_already(user_id: int, date_str: str):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT train_date FROM visit_fact WHERE user_id = {user_id} AND train_date = '{date_str}'")
    rows = cursor.fetchall()
    connection.close()
    if rows:
        return True
    else:
        return False


def get_plan_answer_by_date_and_id(user_id: int, date: str):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT answer, skip_reason FROM visit_plan WHERE user_id = {user_id} "
                   f"AND train_date = '{date}'")
    rows = cursor.fetchall()
    connection.close()

    if rows:
        return rows[0]
    else:
        return []


def get_fact_by_date_and_id(user_id: int, date: str):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT answer FROM visit_fact WHERE user_id = {user_id} "
                   f"AND train_date = '{date}'")
    rows = cursor.fetchall()
    connection.close()

    if rows:
        return rows[0]
    else:
        return []


def get_visit_fact_row(date: str):
    connection = database.getConnection()
    cursor = connection.cursor()
    visit_fact_row = "SELECT user.id, user.firstname, user.lastname, answer " \
                     "FROM visit_fact " \
                     "JOIN user ON user.id = visit_fact.user_id " \
                     f"WHERE train_date = '{date}' " \
                     "ORDER BY lastname, firstname "
    cursor.execute(visit_fact_row)
    result = cursor.fetchall()
    connection.close()
    return result


def insert_visit_fact_row(user_id: int, date_str: str, answer: int):
    timestamp = datetime.datetime.today().strftime("%d-%m-%Y %H:%M:%S")

    connection = database.getConnection()
    cursor = connection.cursor()
    insert_row = f"INSERT INTO visit_fact (user_id, timestamp, train_date, answer) " \
                 f"VALUES ({user_id}, '{timestamp}', '{date_str}', {answer})"
    cursor.execute(insert_row)
    connection.commit()
    connection.close()


def update_visit_fact_row(user_id: int, date_str: str, answer: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    update_row = f"UPDATE visit_fact SET answer = {answer} " \
                 f"WHERE user_id = {user_id} AND train_date = '{date_str}'"
    cursor.execute(update_row)
    connection.commit()
    connection.close()


def send_notification_to_orgs():
    admins = users.get_admins(False)
    for admin in admins:
        admin_id = admin[0]
        try:
            bot.send_message(admin_id, "Отметьте присутствующих на тренировке людей")
        except telebot.apihelper.ApiTelegramException:
            print(f"Администратор {admin[1]} {admin[2]} еще не начал чат с ботом")
