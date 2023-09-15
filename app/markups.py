import datetime

from telebot import types

import train_schedule
import users
import string_constants
import feedbacks
from telegram_bot_pagination import InlineKeyboardPaginator

import visiting_plan


def main_markup(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    write_feedback_button = types.KeyboardButton(string_constants.WRITE_TO_SUPPORT)
    my_feedbacks_button = types.KeyboardButton(string_constants.MY_FEEDBACKS)
    schedule_button = types.KeyboardButton(string_constants.SCHEDULE_BUTTON)
    my_plan_button = types.KeyboardButton(string_constants.PLAN_FOR_WEEK)
    notifications_button = types.KeyboardButton(string_constants.NOTIFICATIONS)
    note_fact_button = types.KeyboardButton(string_constants.NOTE_FACT)
    msg_from_admin_button = types.KeyboardButton(string_constants.MSG_FROM_ADMIN)
    get_all_report_button = types.KeyboardButton(string_constants.GET_ALL_REPORT)
    get_my_report_button = types.KeyboardButton(string_constants.GET_MY_REPORT)
    if users.is_admin(message.chat.id):
        markup.row_width = 2
        markup.add(
            notifications_button,
            msg_from_admin_button
        )
        if users.is_org(message.chat.id):
            markup.add(note_fact_button)
            markup.add(get_all_report_button)
    markup.add(get_my_report_button)
    markup.add(
        write_feedback_button,
        my_feedbacks_button,
        schedule_button,
        my_plan_button
    )

    return markup


def choose_visit_plan_option():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(string_constants.WATCH_PLAN, callback_data="curr_visit_plan"),
        types.InlineKeyboardButton(string_constants.EDIT_PLAN, callback_data="edit_visit_plan")
    )

    return markup


def choose_recipient_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(string_constants.ORGS, callback_data="write_org"),
        types.InlineKeyboardButton(string_constants.DEVS, callback_data="write_dev")
    )

    return markup


def choose_type_of_feedbacks():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(string_constants.ALL_FEEDBACKS, callback_data="get_all_fb"),
        types.InlineKeyboardButton(string_constants.NEW_FEEDBACKS, callback_data="get_new_fb")
    )
    return markup

def handle_feedback_paging(feedback_id: int, fb_type: str, feedbacks_length: int, page):
    feedback = feedbacks.get_feedback_row(feedback_id)
    current_feedback_status = feedback[5]
    feedback_answer = feedback[6]

    paginator = InlineKeyboardPaginator(feedbacks_length, current_page=page,
                                        data_pattern="fb_page:" + fb_type + ":{page}")

    if current_feedback_status != 'closed' and feedback_answer is None:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.ANSWER_FEEDBACK,
                                       callback_data=f"answer_fb:{feedback_id}")
        )

    paginator.add_before(
        types.InlineKeyboardButton(string_constants.CHANGE_FEEDBACK_STATUS,
                                   callback_data=f"change_feedback_status:{page}:{feedback_id}"),
        types.InlineKeyboardButton(string_constants.DELETE_FEEDBACK, callback_data=f"delete_fb:{fb_type}:{feedback_id}")
    )

    return paginator.markup


def schedule_paging(page=1):
    paginator = InlineKeyboardPaginator(7, page, "sch_page:{page}")

    day_number = page
    day = train_schedule.get_schedule_day(day_number)
    is_already_train_day = day[1] is not None

    if is_already_train_day:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.SET_NEW_TRAIN_TIME, callback_data=f"set_new_time:{day_number}"),
            types.InlineKeyboardButton(string_constants.DELETE_TRAIN_DAY, callback_data=f"delete_train:{day_number}")
        )
    else:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.SET_TRAIN, callback_data=f"set_train:{day_number}")
        )

    return paginator.markup


def change_feedback_status(feedback_id: int, fb_type: str, page: int):
    possible_statuses = ['new', 'in work', 'closed']
    current_status = feedbacks.get_feedback_status(feedback_id)
    possible_statuses.remove(current_status)

    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    for status in possible_statuses:
        button_name = ''
        if status == 'new':
            button_name = string_constants.STATUS_NEW
        elif status == 'in work':
            button_name = string_constants.STATUS_IN_WORK
        else:
            button_name = string_constants.STATUS_CLOSED

        markup.add(
            types.InlineKeyboardButton(button_name,
                                       callback_data=f"change_fb_st:{status}:{fb_type}:{page}:{feedback_id}")
        )

    return markup


def schedule_options_admin():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2

    markup.add(
        types.InlineKeyboardButton(string_constants.CURRENT_SCHEDULE, callback_data="curr_sch"),
        types.InlineKeyboardButton(string_constants.EDIT_SCHEDULE, callback_data="edit_sch")
    )

    return markup


def edit_schedule_options(day):
    day_number = day[0]
    is_already_train_day = day[1] is not None
    markup = types.InlineKeyboardMarkup()

    if is_already_train_day:
        markup.row_width = 2
        markup.add(
            types.InlineKeyboardButton(string_constants.SET_NEW_TRAIN_TIME, callback_data=f"set_new_time:{day_number}"),
            types.InlineKeyboardButton(string_constants.DELETE_TRAIN_DAY, callback_data=f"delete_train:{day_number}")
        )
    else:
        markup.row_width = 1
        markup.add(types.InlineKeyboardButton(string_constants.SET_TRAIN, callback_data=f"set_train:{day_number}"))

    return markup


def my_feedback_pages(my_feedbacks, page: int):
    paginator = InlineKeyboardPaginator(len(my_feedbacks), page, 'my_fb_pages:{page}')
    try:
        current_feedback_id = int(my_feedbacks[page - 1][0])

        paginator.add_before(types.InlineKeyboardButton(string_constants.DELETE_FEEDBACK,
                                                        callback_data=f"delete_my_fb:{current_feedback_id}"))
    except Exception:
        return
    return paginator.markup


def train_schedule_filling(dates_to_fill: list[datetime.date], page: int = 1):
    paginator = InlineKeyboardPaginator(len(dates_to_fill), page, 'sch_filling:{page}')
    current_filling_date = dates_to_fill[page - 1].strftime("%d-%m-%Y")

    paginator.add_before(
        types.InlineKeyboardButton(string_constants.WILL_COME, callback_data=f'will_come:{current_filling_date}'),
        types.InlineKeyboardButton(string_constants.WILL_LATE, callback_data=f"will_late:{current_filling_date}"),
        types.InlineKeyboardButton(string_constants.WILL_NOT_COME,
                                   callback_data=f"will_not_come:{current_filling_date}:{page}")
    )

    return paginator.markup


def choose_fact_visiting(user_id: int, date: str, change_status: int = 0):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(string_constants.IS_HERE, callback_data=f"is_here:{user_id}:{date}:{change_status}"),
        types.InlineKeyboardButton(string_constants.NOT_HERE, callback_data=f"not_here:{user_id}:{date}:{change_status}")
    )
    return markup


def change_or_look_fact_visiting(date: str):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(string_constants.CHANGE_FACT, callback_data=f"change_fact:{date}"),
        types.InlineKeyboardButton(string_constants.LOOK_FACT, callback_data=f"look_fact:{date}")
    )
    return markup


def train_schedule_editing(user_id: int, dates_to_edit: list[datetime.date], page: int = 1):
    paginator = InlineKeyboardPaginator(len(dates_to_edit), page, 'sch_editing:{page}')
    current_editing_date = dates_to_edit[page - 1].strftime("%d-%m-%Y")
    current_plan = visiting_plan.get_plan_for_day(user_id, current_editing_date)
    current_answer = current_plan[4] if current_plan else 3

    if current_answer == 0:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.WILL_LATE,
                                       callback_data=f"will_late_edit:{current_editing_date}:{page}"),
            types.InlineKeyboardButton(string_constants.WILL_NOT_COME,
                                       callback_data=f"will_not_come_edit:{current_editing_date}:{page}")
        )
    elif current_answer == 1:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.WILL_COME,
                                       callback_data=f'will_come_edit:{current_editing_date}:{page}'),
            types.InlineKeyboardButton(string_constants.WILL_NOT_COME,
                                       callback_data=f"will_not_come_edit:{current_editing_date}:{page}")
        )
    elif current_answer == 2:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.WILL_COME,
                                       callback_data=f'will_come_edit:{current_editing_date}:{page}'),
            types.InlineKeyboardButton(string_constants.WILL_LATE,
                                       callback_data=f"will_late_edit:{current_editing_date}:{page}")
        )
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.CHANGE_SKIP_REASON,
                                       callback_data=f"change_skip_reason:{current_editing_date}:{page}")
        )
    else:
        paginator.add_before(
            types.InlineKeyboardButton(string_constants.WILL_COME,
                                       callback_data=f'will_come_edit:{current_editing_date}:{page}'),
            types.InlineKeyboardButton(string_constants.WILL_LATE,
                                       callback_data=f"will_late_edit:{current_editing_date}:{page}"),
            types.InlineKeyboardButton(string_constants.WILL_NOT_COME,
                                       callback_data=f"will_not_come_edit:{current_editing_date}:{page}")
        )

    return paginator.markup
