import asyncio
from google_images_search import GoogleImagesSearch
import aiosqlite as aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import logging
from config import *
from database import *
import openai

logging.basicConfig(level=logging.INFO)
openai.api_key = openai_api
bot = Bot(token=bot_api)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

keyboard = InlineKeyboardMarkup()
button1 = InlineKeyboardButton(text="Да", callback_data="send")
button2 = InlineKeyboardButton(text="Отменить", callback_data="cancel")
keyboard.add(button1, button2)

keyboard2 = InlineKeyboardMarkup(one_time_keyboard=True)
keyboard2.add(button2)

keybrd = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
btn1 = KeyboardButton(text="Добавить группу")
btn2 = KeyboardButton(text="Мои группы")
btn3 = KeyboardButton(text="Запустить рассылку")
keybrd.add(btn1, btn2, btn3)

red = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1)
change_name = InlineKeyboardButton(text="Поменять имя", callback_data="change_name")
change_id = InlineKeyboardButton(text="Поменять id", callback_data="change_id")
delete_question = InlineKeyboardButton(text="Удалить", callback_data="try_delete")
red.add(change_name, change_id, delete_question)

delete = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1)
yes = InlineKeyboardButton(text="Да", callback_data="delete")
no = InlineKeyboardButton(text="Нет", callback_data="don't delete")
delete.add(yes, no)

keyboard3 = InlineKeyboardMarkup(row_width=2)
button11 = InlineKeyboardButton(text="Отправить сейчас", callback_data="send_now")
button22 = InlineKeyboardButton(text="Отправить в другое время", callback_data="select_time")
keyboard3.add(button11, button22, button2)

keyboard4 = InlineKeyboardMarkup(row_width=1)
button4 = InlineKeyboardButton(text="Пропустить", callback_data="continue")
keyboard4.add(button4, button2)


class States(StatesGroup):
    name = State()
    enter_id = State()
    send = State()
    enter_photo = State()
    enter_text = State()
    select = State()
    delete = State()
    sent = State()
    select_time = State()
    do_send = State()
    edit_name = State()
    edit_id = State()


@dp.message_handler(commands=['start'])
async def start(message: types.Message, state=FSMContext):
    await message.reply("Вы перешли в главное меню", reply_markup=keybrd)


@dp.message_handler(state='*', commands='Назад')
@dp.message_handler(Text(equals='Назад', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Вы перешли в главное меню', reply_markup=keybrd)


@dp.callback_query_handler(lambda call: call.data == 'cancel', state='*')
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await callback.message.edit_text(text="Вы перешли в главное меню")


@dp.message_handler(Text(equals="Добавить группу"))
async def startPlz(message: types.Message):
    await message.reply("Отправьте отображаемое имя группы/канала.", reply_markup=keyboard2)
    await States.enter_id.set()


@dp.message_handler(Text(equals="Запустить рассылку"))
async def startPlz(message: types.Message, state: FSMContext):
    mgs = await bot.send_message(message.chat.id,
                                 "Отправьте фотографию для рассылки либо запрос, который найдет для вас фотографию",
                                 reply_markup=keyboard4)
    await state.update_data(photo=None)
    await state.update_data(message_id=mgs.message_id)
    await States.enter_photo.set()


@dp.callback_query_handler(lambda call: call.data == 'continue', state=States.enter_photo)
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    a = await state.get_data()
    mgs = await bot.edit_message_text(chat_id=callback.from_user.id, message_id=a['message_id'],
                                 text="Введите текст для рассылки.\nЕсли вы хотите, чтобы текст генерировала нейросеть, поставьте перед сообщением !",
                                 reply_markup=keyboard2)
    await state.update_data(message_id=mgs.message_id)
    await States.enter_text.set()


@dp.message_handler(content_types=['text'], state=States.enter_photo)
async def startPlz(message: types.Message, state: FSMContext):
    gis = GoogleImagesSearch(google_api, cx)
    search_params = {
        "q": message.text,
        "num": 1,  # Количество изображений для получения
        "safe": "high",  # Уровень безопасности: "high", "medium" или "off"
        "fileType": "jpg|png",  # Типы файлов изображений для поиска
        "imgType": "photo",
    }

    gis.search(search_params)
    results = gis.results()
    a = None
    for i, image in enumerate(results):
        a = image.url
    photo = await bot.send_photo(message.from_user.id, a, caption="Ваша фотография:")
    await state.update_data(q=message.text)

    mgs = await bot.send_message(message.chat.id,
                                 "Введите текст для рассылки.\nЕсли вы хотите, чтобы текст генерировала нейросеть, поставьте перед сообщением !",
                                 reply_markup=keyboard2)
    await state.update_data(message_id=mgs.message_id)
    await state.update_data(photo=photo.photo[-1].file_id)
    await States.enter_text.set()


@dp.message_handler(content_types=['photo'], state=States.enter_photo)
async def startPlz(message: types.Message, state: FSMContext):
    mgs = await bot.send_message(message.chat.id,
                                 "Фотография сохранена!\nВведите текст для рассылки.\nЕсли вы хотите, чтобы текст генерировала нейросеть, поставьте перед сообщением !",
                                 reply_markup=keyboard2)
    await state.update_data(photo=message.photo[-1].file_id)
    await state.update_data(message_id=mgs.message_id)
    await States.enter_text.set()


@dp.message_handler(state=States.enter_text)
async def nice(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text.startswith("!"):
        mgs = await bot.send_message(message.chat.id, "Генерирую текст...")
        completion = openai.Completion.create(
            engine="text-davinci-003",
            prompt=message.text[1:],
            max_tokens=1024,
            temperature=0.5,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        await bot.delete_message(message_id=data["message_id"], chat_id=message.chat.id)
        print(completion.choices[0].text)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=mgs.message_id,
                                    text="Ваш текст:" + completion.choices[0].text)
        await state.update_data(aboba=completion.choices[0].text)
    else:
        await state.update_data(aboba=message.text)
        a = await state.get_data()

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute(f"SELECT name, chatid, selected FROM users WHERE userid={message.from_user.id}")
    rows = cursor.fetchall()
    names = []

    for row in rows:
        name = row[0]
        selected = row[2]
        if selected:
            names.append(name + " ✔")
        else:
            names.append(name)

    ids = []
    for row in rows:
        idone = row[1]
        ids.append(idone)

    if names is not None:
        keyboard22 = types.InlineKeyboardMarkup(row_width=1)
        button_list = [types.InlineKeyboardButton(text=names[x], callback_data=f"name:{ids[x]}") for x in
                       range(len(names))]
        keyboard22.add(*button_list)
        keyboard22.add(InlineKeyboardMarkup(text="Отправить✅", callback_data="select_smth"))
        keyboard22.add(InlineKeyboardMarkup(text="Отменить❌", callback_data="cancel"))
        await bot.send_message(message.chat.id, "Выберите группы", reply_markup=keyboard22)
        await state.update_data(names=names)
        await state.update_data(ids=ids)
        await States.select.set()


@dp.message_handler(Text(equals="Мои группы"))
async def startPlz(message: types.Message, state: FSMContext):
    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute(f"SELECT name, chatid FROM users WHERE userid={message.chat.id}")
    rows = cursor.fetchall()
    names = []
    for row in rows:
        name = row[0]
        names.append(name)
    ids = []
    for row in rows:
        idone = row[1]
        ids.append(idone)
    if names is not None:
        keyboard22 = types.InlineKeyboardMarkup(row_width=1)
        button_list = [types.InlineKeyboardButton(text=names[x], callback_data=f"remade:{ids[x]}") for x in
                       range(len(names))]
        keyboard22.add(*button_list)
        if bool(button_list):
            await message.reply("Ваши группы", reply_markup=keyboard22)
            await state.update_data(names=names)
            await state.update_data(ids=ids)

        else:
            await message.reply("Вы еще не добавляли группы/каналы")


@dp.callback_query_handler(lambda c: c.data.startswith('name:'), state=States.select)
async def idk(call: types.CallbackQuery, state: FSMContext):
    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute(
        f"SELECT selected FROM users WHERE userid={call.from_user.id} and chatid = {call.data.split(':')[1]}")
    a = cursor.fetchone()
    if a[0] == 0:
        cursor.execute(
            f"Update users set selected = 1 where userid={call.from_user.id} and chatid = {call.data.split(':')[1]}")
        sqlite_connection.commit()
    elif a[0] == 1:
        cursor.execute(
            f"Update users set selected = 0 where userid={call.from_user.id} and chatid = {call.data.split(':')[1]}")
        sqlite_connection.commit()

    cursor.execute(f"SELECT name, chatid, selected FROM users WHERE userid={call.from_user.id}")
    rows = cursor.fetchall()
    names = []
    for row in rows:
        name = row[0]
        selected = row[2]
        if selected:
            names.append(name + " ✔")
        else:
            names.append(name)

    ids = []
    for row in rows:
        idone = row[1]
        ids.append(idone)
    if names is not None:
        keyboard22 = types.InlineKeyboardMarkup(row_width=1)
        button_list = [types.InlineKeyboardButton(text=names[x], callback_data=f"name:{ids[x]}") for x in
                       range(len(names))]
        keyboard22.add(*button_list)
        keyboard22.add(InlineKeyboardMarkup(text="Отправить✅", callback_data="select_smth"))
        keyboard22.add(InlineKeyboardMarkup(text="Отменить❌", callback_data="cancel"))
        a = await state.get_data()
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Выберите группы", reply_markup=keyboard22)
        a = await state.get_data()
        await state.update_data(names=names)
        await state.update_data(ids=ids)
        await States.select.set()


@dp.callback_query_handler(lambda c: c.data == "select_smth", state=States.select)
async def handle_callback_query(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Когда вы хотите отправить рассылку?", reply_markup=keyboard3)


@dp.callback_query_handler(lambda c: c.data == "send_now", state=States.select)
async def handle_callback_query(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute(f"SELECT chatid FROM users WHERE userid={call.from_user.id} and selected = 1")
    a = cursor.fetchall()
    for i in a:
        if data['photo'] is not None:
            await bot.send_photo(i[0], photo=data['photo'], caption=data['aboba'])
        else:
            await bot.send_message(i[0], data['aboba'])
    await call.message.edit_text("Все сообщения отправлены!")
    await state.finish()


@dp.callback_query_handler(lambda c: c.data == "select_time", state=States.select)
async def handle_callback_query(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Введите время в формате год-месяц-день часы:минуты:секунды\nПример: 2023-07-09 15:18:00",
        reply_markup=keyboard2)
    await States.select_time.set()


@dp.message_handler(state=States.select_time)
async def handle_time(message: types.Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, '%Y-%m-%d %H:%M:%S')
        await state.update_data(date=date)
        await States.do_send.set()
        data = await state.get_data()
        sqlite_connection = sqlite3.connect('database.db')
        cursor = sqlite_connection.cursor()
        cursor.execute(f"SELECT chatid FROM users WHERE userid={message.from_user.id} and selected = 1")
        a = cursor.fetchall()
        for i in a:
            print(data)
            if data['photo'] is not None:
                cursor.execute(f"INSERT INTO sending (chatid, time, text, photo) VALUES ({i[0]}, '{date}', '{data['aboba']}', '{data['photo']}');")
            else:
                cursor.execute(
                    f"INSERT INTO sending (chatid, time, text) VALUES ({i[0]}, '{date}', '{data['aboba']}');")
            sqlite_connection.commit()
        await message.reply("Все сообщения были запланированы!")
        await state.finish()

    except Exception as e:
        print(e)
        await bot.send_message(message.chat.id, "Введите дату правильно")
        await States.select_time.set()


@dp.callback_query_handler(lambda c: c.data.startswith('remade:'))
async def remade_group(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(arg=call.data.split(":"))
    data = await state.get_data()
    await call.message.edit_text(f"Id группы: {data['arg'][1]}\nДействия с группой:", reply_markup=red)


@dp.callback_query_handler(lambda c: c.data == 'try_delete')
async def delete_question(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Удалить группу?", reply_markup=delete)


@dp.callback_query_handler(lambda c: c.data == 'change_name')
async def enter_new_name(call: types.CallbackQuery, state: FSMContext):
    msg = await call.message.edit_text("Введите новое имя для группы", reply_markup=keyboard2)
    await state.update_data(change_message=msg.message_id)
    await States.edit_name.set()


@dp.message_handler(state=States.edit_name)
async def new_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    print(data)
    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE userid = ? AND chatid = ?",
                   (message.text, message.from_user.id, data['arg'][1]))
    sqlite_connection.commit()
    await state.finish()
    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute(f"SELECT name, chatid FROM users WHERE userid={message.chat.id}")
    rows = cursor.fetchall()
    names = []
    for row in rows:
        name = row[0]
        names.append(name)
    ids = []
    for row in rows:
        idone = row[1]
        ids.append(idone)
    if names is not None:
        keyboard22 = types.InlineKeyboardMarkup(row_width=1)
        button_list = [types.InlineKeyboardButton(text=names[x], callback_data=f"remade:{ids[x]}") for x in
                       range(len(names))]
        keyboard22.add(*button_list)
        if bool(button_list):
            await bot.edit_message_text("Имя изменено!", message.from_user.id, data['change_message'])
            await bot.send_message(message.from_user.id, "Ваши группы:", reply_markup=keyboard22)
            await state.update_data(names=names)
            await state.update_data(ids=ids)

        else:
            await message.reply("Вы еще не добавляли группы/каналы")


@dp.callback_query_handler(lambda c: c.data == 'change_id')
async def enter_new_id(call: types.CallbackQuery, state: FSMContext):
    msg = await call.message.edit_text("Введите новое id", reply_markup=keyboard2)
    await state.update_data(change_message=msg.message_id)
    await States.edit_id.set()


@dp.message_handler(state=States.edit_id)
async def new_id(message: types.Message, state: FSMContext):
    try:
        await bot.get_chat(message.text)
        await state.update_data(newChatId=message.text)
        data = await state.get_data()
        sqlite_connection = sqlite3.connect('database.db')
        cursor = sqlite_connection.cursor()
        print(data['names'][0], message.from_user.id, message.text)
        cursor.execute("UPDATE users SET chatid = ? WHERE userid = ? AND name = ?",
                       (message.text, message.from_user.id, data['names'][0]))
        sqlite_connection.commit()
        await state.finish()
        sqlite_connection = sqlite3.connect('database.db')
        cursor = sqlite_connection.cursor()
        cursor.execute(f"SELECT name, chatid FROM users WHERE userid={message.chat.id}")
        rows = cursor.fetchall()
        names = []
        for row in rows:
            name = row[0]
            names.append(name)
        ids = []
        for row in rows:
            idone = row[1]
            ids.append(idone)
        if names is not None:
            keyboard22 = types.InlineKeyboardMarkup(row_width=1)
            button_list = [types.InlineKeyboardButton(text=names[x], callback_data=f"remade:{ids[x]}") for x in
                           range(len(names))]
            keyboard22.add(*button_list)
            if bool(button_list):
                await bot.edit_message_text("id изменен!", message.from_user.id, data['change_message'])
                await bot.send_message(message.from_user.id, "Ваши группы:", reply_markup=keyboard22)
                await state.update_data(names=names)
                await state.update_data(ids=ids)

            else:
                await message.reply("Вы еще не добавляли группы/каналы")
    except Exception as e:
        print(e)
        await message.answer(
            "Пожалуйста, введите действительный id группы/канала. \nБот также должен находится в канале и иметь права на отправку сообщений.",
            reply_markup=keyboard2)


@dp.callback_query_handler(lambda call: call.data == 'delete')
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    a = await state.get_data()
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute(f"""DELETE from users where userid = ? and chatid = ?""", (callback.from_user.id, a['arg'][1]))
    conn.commit()
    await callback.message.edit_text("Удалено!")


@dp.callback_query_handler(lambda call: call.data == "don't delete")
async def dont_delete(callback: types.CallbackQuery, state: FSMContext):
    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()
    cursor.execute(f"SELECT name, chatid FROM users WHERE userid={callback.from_user.id}")
    rows = cursor.fetchall()
    names = []
    for row in rows:
        name = row[0]
        names.append(name)

    ids = []
    for row in rows:
        idone = row[1]
        ids.append(idone)
    if names is not None:
        keyboard22 = types.InlineKeyboardMarkup(row_width=1)
        button_list = [types.InlineKeyboardButton(text=names[x], callback_data=f"remade:{ids[x]}") for x in
                       range(len(names))]
        keyboard22.add(*button_list)
        if bool(button_list):
            await callback.message.edit_text("Ваши группы", reply_markup=keyboard22)
            await state.update_data(names=names)
            await state.update_data(ids=ids)
        else:
            await callback.message.edit_text("Вы еще не добавляли группы/каналы")


# ввод id группы
@dp.message_handler(state=States.enter_id)
async def nice(message: types.Message, state: FSMContext):
    await state.update_data(textMessage=message.text)
    await message.answer("Введите id группы", reply_markup=keyboard2)
    await States.name.set()


# ввод чего-то не знаю
@dp.message_handler(state=States.name)
async def chatId(message: types.Message, state: FSMContext):
    try:
        chat = await bot.get_chat(message.text)
        await state.update_data(chatId=message.text)
        data = await state.get_data()
        await message.answer(f"Добавить группу/канал?\nимя: {data['textMessage']}\nайди: {data['chatId']}",
                             reply_markup=keyboard)
        await States.send.set()
    except Exception as e:
        print(e)
        await message.answer(
            "Пожалуйста, введите действительный id группы/канала. \nБот также должен находится в канале и иметь права на отправку сообщений.",
            reply_markup=keyboard2)
        await States.name.set()


@dp.callback_query_handler(lambda call: call.data == 'send', state=States.send)
async def sent(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        user = (call.from_user.id, data['chatId'], data['textMessage'], False)
        cur.execute("INSERT INTO users VALUES(?, ?, ?, ?);", user)
        conn.commit()
        await call.message.edit_text("Добавлено!")
    except Exception as e:
        print(e)
        await call.message.edit_text("Произошла ошибка. Проверьте правильность введенных данных.")
    await state.finish()


async def time():
    while True:
        current_time = datetime.now().replace(second=0, microsecond=0)
        conn = await aiosqlite.connect("database.db")
        cur = await conn.cursor()
        await cur.execute("SELECT time FROM sending")
        for task_time_tuple in await cur.fetchall():
            task_time = task_time_tuple[0]
            if current_time >= datetime.strptime(task_time, '%Y-%m-%d %H:%M:%S'):
                await cur.execute(f"SELECT chatid, text, photo FROM sending where time='{task_time}'")
                a = await cur.fetchone()
                print(a)
                if a[2] is not None:
                    await bot.send_photo(a[0], photo=a[2], caption=a[1])
                else:
                    await bot.send_message(a[0], a[1])
                await cur.execute("DELETE from sending where time=(?) and chatid = (?)", (task_time, a[0]))
                await conn.commit()
                print("Я что-то удалил")
        await conn.close()
        await asyncio.sleep(60)


if __name__ == '__main__':
    startData()
    loop = asyncio.get_event_loop()
    loop.create_task(time())
    executor.start_polling(dp, skip_updates=True)
