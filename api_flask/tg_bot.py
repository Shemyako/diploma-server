import telebot
import psycopg2
import time
from threading import Thread
import datetime
from dumb import dumb
import os

"""
TO DO
В поток с отправкой уведомлений добавить новый sleep и отправку рекламы
"""

main_user = 424184511
p = 'Token'
bttns = ["Настройки", "Отключить оповещения", "Включить оповещения", "Назад", "Мой id"]
bot = telebot.TeleBot(p)#, threaded=False)
admins = set()
users = set()

@bot.message_handler(commands=['start'])
def first(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
    if (message.from_user.id in admins or message.from_user.id in users):
        itembtn1 = telebot.types.KeyboardButton('Настройки')
        markup.add(itembtn1)

    itembtn2 = telebot.types.KeyboardButton('Мой id')
    markup.add(itembtn2)
    bot.send_message(message.chat.id, 'Приветствую. Свяжитесь с администратором. Если Ваши данные уже есть у администратора,' +
            ' то Вам будут приходить оповещения о грядущих уроках.\nНиже находятся кнопки с настройками', reply_markup=markup)


# Нажатие на кнопку Настойки    
@bot.message_handler(func=lambda message: message.text == "Настройки" and (message.from_user.id in admins or message.from_user.id in users))
def settings_bttn(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
    itembtn1 = telebot.types.KeyboardButton('Отключить оповещения')
    itembtn2 = telebot.types.KeyboardButton('Включить оповещения')
    itembtn3 = telebot.types.KeyboardButton('Назад')
    markup.add(itembtn1)
    markup.add(itembtn2)
    markup.add(itembtn3)
    bot.send_message(message.chat.id, 'Воспользуйтесь кнопками ниже. Если Вы не хотите,' + 
        ' чтобы Вам приходили оповещения о заняхиях, напишите об этом администратору', reply_markup=markup)


# Нажатие на кнопку Отключить оповещения
@bot.message_handler(func=lambda message: message.text == "Отключить оповещения" and (message.from_user.id in admins or message.from_user.id in users))
def trn_on_bttn(message):
    sql = "UPDATE staff SET allowed_to = 0 WHERE tg_id = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (message.from_user.id,))
    conn.commit()
    cursor.close()


# Нажатие на кнопку Включить оповещения
@bot.message_handler(func=lambda message: message.text == "Включить оповещения" and (message.from_user.id in admins or message.from_user.id in users))
def trn_off_bttn(message):
    sql = "UPDATE staff SET allowed_to = 1 WHERE tg_id = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (message.from_user.id,))
    conn.commit()
    cursor.close()


# Нажатие на кнопку Назад
@bot.message_handler(func=lambda message: message.text == "Назад" and (message.from_user.id in admins or message.from_user.id in users))
def back_bttn(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
    itembtn1 = telebot.types.KeyboardButton('Отключить оповещения')
    itembtn2 = telebot.types.KeyboardButton('Включить оповещения')
    itembtn3 = telebot.types.KeyboardButton('Назад')
    markup.add(itembtn1)
    markup.add(itembtn2)
    markup.add(itembtn2)
    bot.send_message(message.chat.id, 'Вы можете нажать на кнопки ниже', reply_markup=markup)


# Нажатие на кнопку Мой id
@bot.message_handler(func=lambda message: message.text == "Мой id")
def get_id_handler(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
    # Если пользователь
    if (message.from_user.id in admins or message.from_user.id in users):
        itembtn1 = telebot.types.KeyboardButton('Настройки')
        markup.add(itembtn1)

    itembtn2 = telebot.types.KeyboardButton('Мой id')
    markup.add(itembtn2)
    bot.send_message(message.from_user.id, "Приветствую. Ваш id - `" + str(message.from_user.id) + "`.\nЧтобы скопировать, нажмите на него. ",
        parse_mode= 'Markdown', reply_markup = markup)


# Пересыл сообщений
@bot.message_handler(func=lambda message: message.from_user.id in admins, content_types=['text'])
def repeat(message):
    if message.forward_from is None:
        bot.send_message(message.from_user.id, "У пользователя запрещён пересыл сообщений")
    else:
        bot.send_message(message.from_user.id, "ID пользователя: `" + str(message.forward_from.id) + "`.\nНажмите по цифрам, чтобы скопировать",
            parse_mode= 'Markdown')                



def main():
    global admins, users

    cursor = conn.cursor()
    ### Сет для админов
    sql = "SELECT tg_id FROM staff WHERE role>1 AND tg_id is not Null"
    cursor.execute(sql)
    pre_admins = cursor.fetchall()
    admins = set(*pre_admins)

    # Сет для пользователей
    sql = "SELECT tg_id FROM staff WHERE role = 0 AND tg_id is not Null"
    cursor.execute(sql)
    pre_admins = cursor.fetchall()
    users = set(*pre_admins)
    cursor.close()

# Отправка оповещений
def send_notifications(day):
    # Получить информацию о занятиях
    sql = ("""SELECT lesson.id, staff.tg_id, staff.phone, staff.name, date, places.name, instructor.name FROM lesson 
		 JOIN places ON places.id = place_id 
		 JOIN dogs ON dogs.id = lesson.dog_id  
         JOIN users_dog ON users_dog.dog_id = dogs.id  
         JOIN staff ON user_id = staff.id 
         JOIN staff as instructor on lesson.staff_id = instructor.id
         WHERE to_char(date, 'DD.MM.YYYY') = %s""")
    cursor = conn.cursor()
    cursor.execute(sql, (day,))
    # Список всех занятий сегодня
    to_notifications_users = cursor.fetchall()
    # print(to_notifications_users)
    
    # Получаем кинологов, у которых сегодня занятия
    sql = """SELECT DISTINCT (staff_id), phone, tg_id FROM lesson
        JOIN staff ON staff.id = staff_id 
        WHERE to_char(date, 'DD.MM.YYYY') = %s"""
    cursor.execute(sql,(day,))
    # Список кинологов
    staff_id = cursor.fetchall()
    cursor.close()
    print(admins)
    
    # Отправляем уведомления клиенту/администратору
    for i in to_notifications_users:
        text_to_send = "Добрый вечер. Завтра у Вас будет занятие.\n" + i[5] + ", " + i[4].strftime("%H:%M") + ", инструктор - " + i[6]
        # print(i)
        # Если есть тг. id, шлём клиенту
        if i[1] is not None:
            # print(i[1])
            try:
                bot.send_message(i[1], text_to_send, parse_mode = 'Markdown')
            except Exception:
                pass
        # Иначе шлём всем админам
        else:
            try:
                for j in admins:
                    bot.send_message(j, "`" + i[2] + "`:\n`" + text_to_send + "`", parse_mode = 'Markdown')
            except Exception:
                pass

    sql = """SELECT date, dog, type_l, place, name FROM (
                SELECT DISTINCT ON (lesson.id) lesson.id, date, dogs.name as dog, 
                types_of_lessons.name as type_l, places.name as place,
                customer.name as name FROM lesson 
                JOIN types_of_lessons ON type_of_lesson = types_of_lessons.id 
                JOIN staff ON staff_id = staff.id 
                JOIN dogs ON dogs.id = dog_id 
                JOIN users_dog ON users_dog.dog_id = dogs.id 
                JOIN staff as customer ON customer.id = users_dog.user_id 
                JOIN places ON place_id = places.id 
                WHERE lesson.staff_id = %s and to_char(date, 'DD.MM.YYYY') = %s) t
            ORDER BY date
            """
    cursor = conn.cursor()
    # Отправляем уведомелния кинологам
    for i in staff_id:
        cursor.execute(sql, (i[0], day))
        lesson_info = cursor.fetchall()
        text_to_send = "Расписание за завтра: "
        for j in lesson_info:
            text_to_send += "\n" + j[0].strftime("%H:%M") + "| " + j[1] + "| " + j[3] + "| " + j[2] + "| " + j[4]
        # Если есть tg_id, шлём кинологу
        if i[2] is not None:
            try:
                bot.send_message(i[1], "`" + text_to_send + "`", parse_mode = 'Markdown')
            except Exception:
                pass
        # Иначе шлём всем админам
        else:
            try:
                for j in admins:
                    bot.send_message(j, "К `" + i[1] + "`:\n`" + text_to_send + "`", parse_mode = 'Markdown')
            except Exception:
                pass


# Оповещения пользователям
def notifications():
    while True:
        today = datetime.datetime.today()
        if today.hour > 17:
            # Находим завтра
            t = today + datetime.timedelta(days=1)
        else:
            t = today
        # Сколько секунд до завтра 18:00
        t = datetime.datetime(t.year, t.month, t.day, 18) - datetime.datetime.today()
        print(t.total_seconds())
        # Спим
        time.sleep(t.total_seconds())
        # Отправляем уведомления на завтрашние занятия
        send_notifications((datetime.date.today()+ datetime.timedelta(days=1)).strftime("%d.%m.%Y"))
        cursor = conn.cursor()
        dumb(cursor)
        cursor.close()
        main()
        with open('./table_dump.sql', 'rb') as doc:
            bot.send_document(main_user, doc)
        os.remove('./table_dump.sql')


try:
    with open('conf.txt', 'r') as f:
        conf = f.read()
    conf = conf.split('~')
    conn = psycopg2.connect(dbname=conf[0], user=conf[1],
                            password=conf[2], host=conf[3])
except FileNotFoundError:
    raise FileNotFoundError('Файл не найден. Проверьте файл conf.txt в дирректории')
except IndexError:
    raise IndexError('Файл conf.txt заполнен неверно. Проверьте его и перезапустите программу')
except psycopg2.OperationalError:
    raise psycopg2.OperationalError('В файле conf.txt указаны некорректные данные. Подключение к БД сорвалось.')


# th1 = Thread(target=main, daemon=True)
th2 = Thread(target=notifications, daemon=True)
th2.start()
# th1.start()
main()

# while True:
#     try:
bot.polling(none_stop=True)
    # except KeyboardInterrupt:
    #     print('Ola')
    #     return
    # except Exception as e:
    #     print(e)
# th1.join(1)
th2.join(1)