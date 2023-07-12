import sqlite3
from datetime import datetime, timedelta


def startData():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
       userid INT,
       chatid INT,
       name TEXT,
       selected BOOLEAN);
    """)
    cur.execute("""CREATE TABLE IF NOT EXISTS sending(
       chatid INT,
       time TEXT,
       text TEXT,
       photo TEXT);
    """)
    cur.execute("SELECT * FROM sending")
    rows = cur.fetchall()

    # Вывод данных
    for row in rows:
        print(row)

    # Закрытие соединения
    conn.close()
