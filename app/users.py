import database
import string_constants
from telebot import types
import config
import markups
from msg_check import check

bot = config.bot
msg = ""


def is_registered(user_id: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE id={user_id} and isActive=1")
    rows = cursor.fetchall()
    connection.close()

    return len(rows) > 0


def is_org(user_id: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE id={user_id} AND isOrg=1")
    rows = cursor.fetchall()
    connection.close()

    return len(rows) > 0


def is_dev(user_id: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE id={user_id} AND isDev=1")
    rows = cursor.fetchall()
    connection.close()

    return len(rows) > 0


def is_admin(user_id: int):
    return is_dev(user_id) or is_org(user_id)


def get_user(user_id: int):
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    rows = cursor.fetchall()
    connection.close()

    if len(rows) > 0:
        return rows[0]
    else:
        print(f"Пользователя с id = {user_id} не существует")


def get_admins(admin_type: bool):
    sql_condition = "isDev = 1" if admin_type else "isOrg = 1"

    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE {sql_condition} AND isActive = 1 ORDER BY lastname, firstname")
    rows = cursor.fetchall()
    connection.close()

    return rows


def get_user_name(user_id: int) -> str:
    user_row = get_user(user_id)
    return user_row[1] + " " + user_row[2]


def get_active_users():
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE isActive = 1 ORDER BY lastname, firstname")
    rows = cursor.fetchall()
    connection.close()
    return rows

def get_active_users_sorted_inBase():
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user WHERE isActive = 1 ORDER BY inBase DESC, lastname, firstname")
    rows = cursor.fetchall()
    connection.close()
    return rows

def get_all_users():
    connection = database.getConnection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user ORDER BY NOT isActive, lastname, firstname")
    rows = cursor.fetchall()
    connection.close()
    return rows


def show_users_data(message: types.Message):
    users = get_all_users()
    if not users:
        bot.send_message(message.chat.id, "База данных с пользователями пуста", reply_markup=markups.main_markup(message))
        return
    i = 1
    bot.send_message(message.chat.id, "Формат:\n№) " + string_constants.USER_FORMAT, reply_markup=markups.main_markup(message))
    string = ""
    for user in users:
        string += str(i)+") " + str(user[0]) + ":" + user[2] + ":" + \
                 user[1] + ":" + user[3] +  ":" + str(user[4]) + ":"
        if user[5] == 1:
            string += "да:"
        else:
            string += "нет:"
        if user[6] == 1:
            string += "да:"
        else:
            string += "нет:"
        if user[7] == 1:
            string += "да:"
        else:
            string += "нет:"
        string += str(user[8])
        if user[9] == 1:
            string += ":да\n"
        else:
            string += ":нет\n"

        i += 1
    bot.send_message(message.chat.id, string, reply_markup=markups.main_markup(message))


def add_user(message: types.Message):
    form_string = "Введите данные одного пользователя в формате:\n" + string_constants.USER_FORMAT + \
                  "Или напишите: Отмена"
    bot.send_message(message.chat.id, form_string, reply_markup=markups.main_markup(message))
    bot.register_next_step_handler(message, get_user_data_from_msg)


def get_user_data_from_msg(message: types.Message):
    global msg
    msg = message.text
    status = check(str(msg))
    if status == 1:
        bot.send_message(message.chat.id, string_constants.CANCEL_MSG,
                         reply_markup=markups.main_markup(message))
    else:
        array = get_array(msg)
        if not array:
            form_string = "Пожалуйста, введите корректные данные одного пользователя в формате:\n" + \
                          string_constants.USER_FORMAT + "Или напишите: Отмена"
            bot.send_message(message.chat.id, form_string, reply_markup=markups.main_markup(message))
            bot.register_next_step_handler(message, get_user_data_from_msg)
        else:
            bot.send_message(message.chat.id, "Великолепно!", reply_markup=markups.main_markup(message))
            add_user_in_database(array)
            # SUCCESS


def get_array(msg: str):
    array = msg.split(":")
    if not len(array) == 10:
        return []
    try:
        array[0] = int(array[0].strip())
    except:
        return []

    if array[5].lower().strip() == "да":
        array[5] = 1
    elif array[5].lower().strip() == "нет":
        array[5] = 0
    else:
        return []

    if array[6].lower().strip() == "да":
        array[6] = 1
    elif array[6].lower().strip() == "нет":
        array[6] = 0
    else:
        return []

    if array[7].lower().strip() == "да":
        array[7] = 1
    elif array[7].lower().strip() == "нет":
        array[7] = 0
    else:
        return []

    if array[9].lower().strip() == "да":
        array[9] = 1
    elif array[9].lower().strip() == "нет":
        array[9] = 0
    else:
        return []

    return array


def add_user_in_database(array):
    if not get_user(array[0]):
        connection = database.getConnection()
        cursor = connection.cursor()
        insert_row = f"INSERT INTO user (id, lastname, firstname, patronymic, phone, isActive, isOrg, isDev, userGroup, inBase) " \
                     f"VALUES ({array[0]}, '{array[1]}', '{array[2]}', '{array[3]}', '{array[4]}', {array[5]}, {array[6]}, {array[7]}, " \
                     f"{array[8]}, '{array[9]}')"
        cursor.execute(insert_row)
        connection.commit()
        connection.close()
    else:
        connection = database.getConnection()
        cursor = connection.cursor()
        update_row = f"UPDATE user SET lastname = '{array[1]}', firstname = '{array[2]}', patronymic = '{array[3]}', phone = '{array[4]}', " \
                     f"isActive = {array[5]}, isOrg = {array[6]}, isDev = {array[7]}, " \
                     f"userGroup = '{array[8]}', inBase = {array[9]} " \
                     f"WHERE id = {array[0]}"
        cursor.execute(update_row)
        connection.commit()
        connection.close()


def make_root(message: types.Message):
    if get_user(message.chat.id):
        connection = database.getConnection()
        cursor = connection.cursor()
        update_row = f"UPDATE user SET isActive = 1, isDev = 1 " \
                     f"WHERE id = {message.chat.id}"
        cursor.execute(update_row)
        connection.commit()
        connection.close()
        bot.send_message(message.chat.id, "Поздравляю с повышением! Теперь Вы - разработчик 😉",
                         reply_markup=markups.main_markup(message))

