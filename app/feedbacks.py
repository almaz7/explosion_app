import telebot.apihelper
import config
from datetime import datetime
from telebot import types
import database
import markups
import users
import string_constants
from msg_check import check

bot = config.bot

dest = 0
feedback_text = ''
msg_from_admin = ''


@bot.callback_query_handler(lambda query: query.data == "write_org" or query.data == "write_dev")
def choose_dest_cb_handler(query: types.CallbackQuery):
    global dest
    dest = 0 if query.data == "write_org" else 1
    bot.send_message(query.message.chat.id, "Опишите свою проблему или напишите: Отмена")
    bot.delete_message(query.message.chat.id, query.message.message_id)
    bot.register_next_step_handler(query.message, get_feedback_text)


@bot.callback_query_handler(lambda query: query.data == "get_all_fb" or query.data == "get_new_fb")
def get_all_fb_handler(query: types.CallbackQuery):
    feedbacks = get_feedbacks(query.message, query.data, sort_by_new=True)

    if len(feedbacks) > 0:
        bot.send_message(query.message.chat.id, f"{'Новые' if query.data == 'get_new_fb' else 'Все'} уведомления:")
        send_feedback_page(query.message, feedbacks, query.data)
    else:
        bot.send_message(query.message.chat.id,
                         f"На данный момент нет {'новых ' if query.data == 'get_new_fb' else ''}обращений")


@bot.callback_query_handler(lambda query: query.data.startswith('answer_fb:'))
def handle_with_feedback(query: types.CallbackQuery):
    try:
        feedback_id = int(query.data.split(':')[1])
        feedback = get_feedback_row(feedback_id)
    except Exception:
        feedback = None

    if feedback is None:
        bot.send_message(query.message.chat.id, "Данное обращение отсутствует.")
        return

    feedback_status = feedback[5]
    admin_id = query.message.chat.id

    if feedback_status == 'closed' or feedback[6] is not None:
        bot.send_message(query.message.chat.id, "Ответ на обращение запрещен.")
    else:
        bot.send_message(query.message.chat.id, "Напишите ответ пользователю.")
        bot.register_next_step_handler(query.message,
                                       write_feedback_answer(feedback, admin_id))


@bot.callback_query_handler(lambda query: query.data.startswith('change_feedback_status:'))
def handle_with_feedback(query: types.CallbackQuery):
    try:
        feedback_id = int(query.data.split(':')[2])
        page = int(query.data.split(':')[1])
        feedback = get_feedback_row(feedback_id)
    except Exception:
        feedback = None

    if feedback is None:
        bot.send_message(query.message.chat.id, "Данное обращение отсутствует.")
        return

    feedback_status = feedback[5]
    fb_type = "get_new_fb" if feedback_status == 'new' else "get_all_fb"

    bot.delete_message(query.message.chat.id, query.message.message_id)
    bot.send_message(query.message.chat.id, query.message.text,
                     reply_markup=markups.change_feedback_status(feedback_id, fb_type, page))


@bot.callback_query_handler(lambda query: query.data.startswith('change_fb_st:'))
def handle_status_changing(query: types.CallbackQuery):
    new_status, fb_type, page, feedback_id = query.data.split(':')[1:]
    try:
        page = int(page)
        feedback_id = int(feedback_id)
        feedback = get_feedback_row(feedback_id)
    except Exception:
        feedback = None

    if feedback is None:
        bot.send_message(query.message.chat.id, "Данное обращение отсутствует.")
        return

    _, user_id, _, feedback_txt, _, old_status, _ = feedback
    admin_id = query.message.chat.id

    update_feedback_status(feedback_id, new_status)
    bot.delete_message(query.message.chat.id, query.message.message_id)
    send_feedback_page(query.message, get_feedbacks(query.message, fb_type, True), fb_type, page)
    send_notification_to_admins(users.is_dev(admin_id),
                                f"Администратор {users.get_user_name(admin_id)} поменял статус обращения от пользователя"
                                f" {users.get_user_name(user_id)}: \n{feedback_txt}\nc *{old_status}* на *{new_status}*.",
                                excluded_ids=[query.message.chat.id])


@bot.callback_query_handler(lambda query: query.data.startswith('my_fb_pages:'))
def handle_my_feedbacks_paging(query: types.CallbackQuery):
    try:
        page = int(query.data.split(':')[1])
        bot.delete_message(query.message.chat.id, query.message.message_id)
        send_my_feedbacks_page(query.message, get_user_feedbacks(query.message.chat.id), page)
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")


@bot.callback_query_handler(lambda query: query.data.startswith('delete_fb:'))
def delete_feedback_handle(query: types.CallbackQuery):
    try:
        feedback_id = int(query.data.split(':')[2])
        fb_type = query.data.split(':')[1]

        delete_feedback(feedback_id)
        bot.delete_message(query.message.chat.id, query.message.message_id)
        send_feedback_page(query.message, get_feedbacks(query.message, fb_type, True), fb_type)
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")


@bot.callback_query_handler(lambda query: query.data.startswith('delete_my_fb:'))
def delete_my_fb(query: types.CallbackQuery):
    try:
        feedback_id = int(query.data.split(':')[1])
        delete_feedback(feedback_id)
        bot.delete_message(query.message.chat.id, query.message.message_id)
        send_my_feedbacks_page(query.message, get_user_feedbacks(query.message.chat.id))
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")


@bot.callback_query_handler(lambda query: query.data.startswith('fb_page:'))
def feedback_page_callback(query: types.CallbackQuery):
    cb_args = query.data.split(':')
    try:
        page = int(cb_args[2])
        fb_type = cb_args[1]

        bot.delete_message(query.message.chat.id, query.message.message_id)
        send_feedback_page(query.message, get_feedbacks(query.message, fb_type, sort_by_new=True), fb_type, page)
    except Exception:
        bot.send_message(query.message.chat.id, "Произошла непредвиденная ошибка. Попробуйте повторить запрос")


def get_feedback_text(message: types.Message):
    global feedback_text
    feedback_text = message.text
    status = check(str(feedback_text))
    if status == 1:
        bot.send_message(message.chat.id, string_constants.CANCEL_MSG,
                         reply_markup=markups.main_markup(message))
        return
    message_caption = message.caption

    if feedback_text is None and message_caption is None:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте сообщение, содержащее текст или напишите: Отмена")
        bot.register_next_step_handler(message, get_feedback_text)
    elif message_caption is not None:
        feedback_text = message_caption
        bot.send_message(message.chat.id, "Внимание! Прикрепленный вами файл не будет виден администраторам!")

    send_feedback(message)
    send_notification_to_admins(bool(dest), "Пришло новое уведомление!")
    bot.send_message(message.chat.id, f"Спасибо за обращение! В скором времени мы решим ваш вопрос.",
                     reply_markup=markups.main_markup(message))


def send_feedback(message: types.Message):
    global dest, feedback_text
    user_id = message.chat.id
    timestamp = datetime.today().strftime("%d-%m-%Y %H:%M:%S")
    text = feedback_text
    recipient = dest
    status = "new"

    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    sql_insert_feedback = f"INSERT INTO feedback (user_id, timestamp, feedback_text, recipient, status) " \
                          f"VALUES ({user_id}, '{timestamp}', '{text}', {recipient}, '{status}')"
    cursor.execute(sql_insert_feedback)
    db_connection.commit()
    db_connection.close()


def feedback_string(feedback_row) -> str:
    user = users.get_user(feedback_row[1])
    answer = f"\n*Ответ на обращение*: \n{feedback_row[6]}" if feedback_row[6] is not None else ""

    result = f"*Время обращения*: {feedback_row[2]}\n" \
             f"*Отправитель*: {user[1] + ' ' + user[2]}\n" \
             f"*Обращение*: \n{feedback_row[3]}\n" \
             f"*Адресат*: {'Орг' if feedback_row[4] == 0 else 'Разработчик'}\n" \
             f"*Статус*: {feedback_row[5]}" \
             f"{answer}"

    return result


def get_feedbacks(message: types.Message, feedback_type: str, sort_by_new: bool):
    user_id = message.chat.id
    sql_feedback_type_specifier_and = "status='new' AND" if feedback_type == "get_new_fb" else ""
    sql_feedback_type_specifier_where = "WHERE status='new'" if feedback_type == "get_new_fb" else ""
    ordering_string = " ORDER BY timestamp DESC" if sort_by_new else ""

    if users.is_admin(user_id):
        db_connection = database.getConnection()
        cursor = db_connection.cursor()

        if users.is_dev(user_id) and users.is_org(user_id):
            cursor.execute(f"SELECT * FROM feedback {sql_feedback_type_specifier_where} {ordering_string};")
        else:
            cursor.execute(f"SELECT * FROM feedback "
                           f"WHERE {sql_feedback_type_specifier_and} recipient= {0 if users.is_org(user_id) else 1}"
                           f"{ordering_string};")
        feedbacks = cursor.fetchall()
        db_connection.close()

        return feedbacks
    else:
        print("Запрос на фидбеки от пользователя, не являющегося админом")


def send_feedback_page(message: types.Message, feedbacks, fb_type: str, page=1):
    if feedbacks:
        try:
            feedback_id = int(feedbacks[page - 1][0])
        except IndexError:
            bot.send_message(message.chat.id, "Некоторые уведомления были удалены. "
                                              "Для просмотра обновленных данных нажмите на Уведомления")
            return
        bot.send_message(message.chat.id, feedback_string(feedbacks[page - 1]),
                         reply_markup=markups.handle_feedback_paging(feedback_id, fb_type, len(feedbacks), page),
                         parse_mode='Markdown')


def send_my_feedbacks_page(message: types.Message, my_feedbacks, page=1):
    if my_feedbacks:
        try:
            my_feedbacks[page - 1]
        except IndexError:
            bot.send_message(message.chat.id, "Некоторые уведомления были удалены. "
                                              "Для просмотра обновленных данных нажмите на Мои обращения")
            return
        bot.send_message(message.chat.id, feedback_string(my_feedbacks[page - 1]),
                         reply_markup=markups.my_feedback_pages(my_feedbacks, page), parse_mode='Markdown')


def write_feedback_answer(feedback, admin_id: int):
    return lambda message: write_feedback_answer_aux(message, feedback, admin_id)


def write_feedback_answer_aux(message, feedback, admin_id: int):
    feedback_id = feedback[0]
    user_id = feedback[1]
    admin = users.get_user(admin_id)
    user = users.get_user(user_id)
    feedback_recipient = bool(feedback[4])
    fb_text = feedback[3]

    answer_to_feedback = message.text

    if message.text is None and message.caption is None:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте сообщение, содержащее текст")
        bot.register_next_step_handler(message, write_feedback_answer(feedback, admin_id))
        return
    elif message.caption is not None:
        bot.send_message(message.chat.id, "Внимание! Прикрепленный вами файл не будет виден пользователю!")
        answer_to_feedback = message.caption

    bot.send_message(user_id, f"Ответ на сообщение: \n{fb_text}\n\n{answer_to_feedback}")
    bot.send_message(message.chat.id, "Сообщение было доставлено пользователю.")
    send_feedback_answer(feedback_id, answer_to_feedback)
    send_notification_to_admins(feedback_recipient, f"Администратор {admin[1]} {admin[2]} ответил "
                                                    f"пользователю {user[1]} {user[2]} на обращение.\n\n"
                                                    f"Ответ на сообщение: \n{fb_text}\n\n{answer_to_feedback}",
                                excluded_ids=[message.chat.id])


def get_my_feedbacks(message: types.Message):
    user_id = message.chat.id
    my_feedbacks = get_user_feedbacks(user_id)

    if len(my_feedbacks) > 0:
        send_my_feedbacks_page(message, my_feedbacks)
    else:
        bot.send_message(message.chat.id, "На данный момент у вас нет обращений.",
                         reply_markup=markups.main_markup(message))


def get_user_id_from_feedback(feedback_id: int):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT user_id FROM feedback WHERE id = {feedback_id}")
    rows = cursor.fetchall()
    db_connection.close()

    if len(rows) > 0:
        return rows[0][0]
    else:
        print("Ошибка обращения к базе данных")
        return None


def get_user_feedbacks(user_id: int):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT * FROM feedback WHERE user_id = {user_id} ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    if len(rows) > 0:
        return rows
    else:
        return []


def get_fb_text(feedback_id: int):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT feedback_text FROM feedback WHERE id = {feedback_id}")
    rows = cursor.fetchall()
    db_connection.close()

    if len(rows) > 0:
        return rows[0][0]
    else:
        print(f"Нет фидбека c id = {feedback_id}")
        return None


def get_feedback_status(feedback_id: int):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT status FROM feedback WHERE id = {feedback_id}")
    rows = cursor.fetchall()
    db_connection.close()

    if len(rows) > 0:
        return rows[0][0]
    else:
        print(f"Нет фидбека c id = {feedback_id}")
        return None


def get_feedback_row(feedback_id: int):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"SELECT * FROM feedback WHERE id = {feedback_id}")
    rows = cursor.fetchall()
    db_connection.close()

    if len(rows) > 0:
        return rows[0]
    else:
        print(f"Нет фидбека c id = {feedback_id}")
        return None


def update_feedback_status(feedback_id: int, new_status: str):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"UPDATE feedback SET status='{new_status}' WHERE id={feedback_id}")
    db_connection.commit()
    db_connection.close()


def delete_feedback(feedback_id: int):
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    cursor.execute(f"DELETE FROM feedback WHERE id = {feedback_id}")
    db_connection.commit()
    db_connection.close()


def send_feedback_answer(feedback_id: int, answer: str) -> bool:
    db_connection = database.getConnection()
    cursor = db_connection.cursor()
    feedback = get_feedback_row(feedback_id)

    if feedback is None:
        db_connection.close()
        return False
    else:
        cursor.execute(f"UPDATE feedback SET feedback_answer = '{answer}' WHERE id = {feedback_id}")
        db_connection.commit()
        db_connection.close()
        return True


def send_notification_to_admins(admin_type: bool, notification_text: str, excluded_ids=None, parse_mode='Markdown'):
    if excluded_ids is None:
        excluded_ids = []
    admins_list = users.get_admins(admin_type)

    for admin in admins_list:
        admin_id = admin[0]

        if admin_id not in excluded_ids:
            try:
                bot.send_message(admin_id, notification_text, parse_mode=parse_mode)
            except telebot.apihelper.ApiTelegramException:
                print(f"Администратор {admin[1]} {admin[2]} еще не начал чат с ботом")
        else:
            continue


def get_msg_from_admin(message: types.Message):
    global msg_from_admin
    msg_from_admin = message.text
    message_caption = message.caption

    if msg_from_admin is None and message_caption is None:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте сообщение, содержащее текст")
        bot.register_next_step_handler(message, get_msg_from_admin)
    elif message_caption is not None:
        msg_from_admin = message_caption
        bot.send_message(message.chat.id, "Внимание! Прикрепленный вами файл не будет виден пользователям!")

    status = check(str(msg_from_admin))
    if status == -1:
        bot.send_message(message.chat.id, "Сообщение должно отличаться от текста кнопки. Попробуйте еще раз или напишите: Отмена",
                         reply_markup=markups.main_markup(message))
        bot.register_next_step_handler(message, get_msg_from_admin)
    elif status == 0:
        send_msg_from_admin(message)
    else:
        bot.send_message(message.chat.id, string_constants.CANCEL_MSG,
                         reply_markup=markups.main_markup(message))


def send_msg_from_admin(message: types.Message):
    global msg_from_admin
    active_users = users.get_active_users()
    admin_id = message.chat.id
    admin = users.get_user(admin_id)
    text = "Новое сообщение от администратора " + admin[1] + " " + admin[2] + ":\n"
    text += str(msg_from_admin)

    for user in active_users:
        user_id = user[0]
        try:
            bot.send_message(user_id, text)
        except telebot.apihelper.ApiTelegramException:
            print(f"Пользователь {user[1]} {user[2]} еще не начал чат с ботом")

    bot.send_message(message.chat.id, f"Сообщение доставлено пользователям",
                     reply_markup=markups.main_markup(message))



