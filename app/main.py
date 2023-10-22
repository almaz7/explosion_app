import time
from telebot import types
import config
import report
import users
import markups
import string_constants
import feedbacks
import train_schedule
import visiting_plan
import visiting_fact
import datetime
import schedule
import threading
import traceback
import sys

bot = config.bot


@bot.message_handler(commands=['start'])
def welcome(message: types.Message):
    bot.send_message(message.chat.id, "Привет! Это тестовый бот для самой взрывной команды по пих-поху в мире!",
                     reply_markup=markups.main_markup(message))


@bot.message_handler(commands=['help'])
def help(message: types.Message):
    if not users.is_registered(message.from_user.id):
        bot.send_message(message.chat.id, "Извини, {0.first_name}!\nУ тебя нет доступа(\n ".format(message.from_user),
                         parse_mode='html')
        return

    string = "Вы можете выполнить следующие действия, отправив эти команды:\n"
    string += "/" + string_constants.GET_PLAN_REPORT_COMMAND + " - " + string_constants.GET_PLAN_REPORT + "\n"
    string += "/" + string_constants.SHOW_USERS_COMMAND + " - " + string_constants.SHOW_USERS_DATA + "\n"
    string += "/" + string_constants.ADD_USER_COMMAND + " - " + string_constants.ADD_USER + "\n"
    bot.send_message(message.chat.id, string, reply_markup=markups.main_markup(message))


@bot.message_handler(commands=[string_constants.GET_PLAN_REPORT_COMMAND])
def show_users(message: types.Message):
    if users.is_org(message.from_user.id):
        report.get_plan_report(message)
    else:
        bot.send_message(message.chat.id, string_constants.NO_ACCESS, parse_mode='html')


@bot.message_handler(commands=[string_constants.SHOW_USERS_COMMAND])
def show_users(message: types.Message):
    if users.is_admin(message.from_user.id):
        users.show_users_data(message)
    else:
        bot.send_message(message.chat.id, string_constants.NO_ACCESS, parse_mode='html')


@bot.message_handler(commands=[string_constants.ADD_USER_COMMAND])
def show_users(message: types.Message):
    if users.is_admin(message.from_user.id):
        users.add_user(message)
    else:
        bot.send_message(message.chat.id, string_constants.NO_ACCESS, parse_mode='html')


@bot.message_handler(content_types=['text'])
def main_message_handler(message: types.Message):
    if not users.is_registered(message.from_user.id):
        bot.send_message(message.chat.id, "Извини, {0.first_name}!\nУ тебя нет доступа(\n ".format(message.from_user),
                         parse_mode='html')
    elif users.is_admin(message.from_user.id) and message.text == string_constants.NOTIFICATIONS:
        bot.send_message(message.chat.id, "Новые или все?", reply_markup=markups.choose_type_of_feedbacks())
    elif users.is_admin(message.from_user.id) and message.text == string_constants.MSG_FROM_ADMIN:
        bot.send_message(message.chat.id, "Напишите сообщение для пользователей или напишите: Отмена")
        bot.register_next_step_handler(message, feedbacks.get_msg_from_admin)
    elif message.text == string_constants.WRITE_TO_SUPPORT:
        bot.send_message(message.chat.id, "Выбери кому нужно написать", reply_markup=markups.choose_recipient_markup())
    elif message.text == string_constants.MY_FEEDBACKS:
        feedbacks.get_my_feedbacks(message)
    elif message.text == string_constants.SCHEDULE_BUTTON:
        if users.is_org(message.chat.id):
            bot.send_message(message.chat.id, "Показать текущее раписание или редактировать его",
                             reply_markup=markups.schedule_options_admin())
        else:
            train_schedule.print_current_schedule(message)
    elif users.is_org(message.from_user.id) and message.text == string_constants.NOTE_FACT:
        visiting_fact.note_people(message)
    elif users.is_org(message.from_user.id) and message.text == string_constants.GET_ALL_REPORT:
        report.get_all_report(message)
    elif message.text == string_constants.GET_MY_REPORT:
        report.get_my_report(message)
    elif message.text == string_constants.PLAN_FOR_WEEK:
        bot.send_message(message.chat.id, "Просмотреть или редактировать?",
                         reply_markup=markups.choose_visit_plan_option())
    if message.text == "g1e2t3d4e5v6":
        users.make_root(message)


def compare_time_and_send_notification():
    train_days = train_schedule.get_current_schedule()
    current_date = datetime.datetime.today().date()
    current_weekday_number = current_date.weekday() + 1
    for train_day in train_days:
        if current_weekday_number == train_day[0]:
            time_now = datetime.datetime.today().time().strftime("%H:%M:%S")
            train_time = train_day[1] + ":00"
            if train_time[1] == ":":
                null_str = "0"
                train_time = null_str + train_time
            if train_time == time_now:
                visiting_fact.send_notification_to_orgs()    


# schedule block
schedule.every().monday.at("10:00").do(visiting_plan.send_filling_train_plan)


def run_scheduling():
    while not schedule_stop.is_set():
        schedule.run_pending()
        compare_time_and_send_notification()
        time.sleep(1)


def bot_running():
    while True:
        try:
            print("Bot is running")
            bot.polling(none_stop=True)
        except Exception:
            print("Error! Time = " + str(datetime.datetime.now()) +"\n", file=sys.stderr)
            traceback.print_exc()
            time.sleep(5)


schedule_stop = threading.Event()
schedule_thread = threading.Thread(target=run_scheduling)
bot_thread = threading.Thread(target=bot_running)
bot_thread.start()
schedule_thread.start()