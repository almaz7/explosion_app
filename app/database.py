import sqlite3


def getConnection():
    connection = None
    try:
        connection = sqlite3.connect('exp_bot_db.db')
    except sqlite3.Error as error:
        print("Ошибка при подключении к sqlite", error)

    return connection
