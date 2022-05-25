from flask import Flask, request, g
import hashlib
import uuid
import psycopg2
import time
from datetime import date, datetime, timedelta
import os
from load_db import load
# from dumb import dumb

'''
TO DO

Рассылка сообщений на почту/тг

Убрать MsgBox, сделать первую страницу
html шаблон

Поменять принцип формирования адреса. На главной форме after_route и route 
?Написать тесты и реализовать
Метить людей без тг
логин новому админу
Выбор либо админ либо кинолог. Без одновременного
проверкка на выбор собаки в занятиях + удаление всего
Изменить интерфейс (bttn=>lbl)
Сервер: Доделать дамб в отдельном потоке 
Проверить десктоп + сервер
Сделать телеграм

Запретить вводить &?
Добавить гифку на время ожидания на клиент

'''
app = Flask(__name__)


# Хеширование пароля
def making_hash(password: str):
    # Тут создаю хэш для нового пароля с солью 
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt
    

# Проверка пароля
def check_password(login: int, user_password: str):
    ###
    # Check password in DB and given
    ###

    # Get user info via login
    sql = "SELECT * FROM \"user\" WHERE id = %s"
    cursor = conn.cursor()
    cursor.execute(sql,(login,))
    user_info = cursor.fetchone()
    cursor.close()
    # print(user_info)
    if user_info is None or len(user_info) == 0:
        return False
    # user_info: id (login); password; staff_id (user's id, who own this pass)
    password, salt = user_info[1].split(':')
    return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()


# Создание токена для сессии   
def making_token_for_session(login: int, ip: str, mac: str):
    ctime = time.time()
    token = uuid.uuid4().hex
    cursor = conn.cursor()
    # Получаем старый токен, удалим его из словаря
    sql = "SELECT token FROM sessions WHERE user_id=%s AND token is not Null"
    cursor.execute(sql, (login,))
    token_before_delete = cursor.fetchone()
    if token_before_delete is not None:
        users_roles.pop(token_before_delete[0])
    
    # Очистим сессии, создадим новые, вернём токен и роль
    sql = "UPDATE sessions SET token = Null WHERE user_id = %s AND token is not Null"
    cursor.execute(sql,(login,))
    conn.commit()
    sql = "INSERT INTO sessions(user_id, token, time, ip, mac) VALUES(%s,%s,%s,%s,%s)"
    cursor.execute(sql,(login, str(ctime)+token , ctime, ip, mac))
    conn.commit()
    sql = "SELECT role FROM staff JOIN \"user\" ON staff_id = staff.id WHERE \"user\".id = %s"
    cursor.execute(sql, (login,))
    role = cursor.fetchone()
    cursor.close()
    users_roles[str(ctime) + token] = role[0]
    # print(users_roles)
    return str(ctime) + token, role 


# Auth check
@app.before_request
def before_request():
    # Если пользователь авторизуется, то нет смысла проверять его сессию
    if request.path == "/login":
        return 
    # Если нет в запросе логина мака токена
    elif "token" not in request.args or "mac" not in request.args: # or "login" not in request.args:
        # Заставляем переавторизироваться
        return "-1~"
    
    # Получаем информацию о сессии пользователя с конкретным токеном и мак 
    sql = "SELECT * FROM sessions WHERE token=%s AND mac=%s"
    cursor = conn.cursor();
    cursor.execute(sql,(request.args.get("token"), request.args.get("mac")))
    user = cursor.fetchone()
    cursor.close()
    print(users_roles)
    # print(user)
    if user is None :
        # Если сессии нет, то реавторизация
        return "-1~Вам нужно пройти заново авторизацию"
    elif len(user) != 0 and (time.time() - user[3]) < 3600:
        # Если сессия есть и время актуально пропускаем
        # print('norm')
        return
    # Если ip и mac пердыдущей сессии не изменился
    elif user[4] == request.remote_addr and user[5] == request.args.get("mac"):
        # Зановов создаём токен без реавторизации
        token, role = making_token_for_session(user[1], request.remote_addr, request.args.get("mac"))
        return "3~" + token
    else:
        # Если время вышло и новый мак/ip
        # Переавторизация
        return "-1~Вам нужно пройти заново авторизацию"


@app.route("/login")
def login():
    # print(request.args)
    # Если пришли логин и пароль
    # return 0 -> bad auth
    # return 1 -> correct auth
    if 'login' in request.args and 'password' in request.args and 'mac' in request.args:

        # try для проверки, логин число ли
        # try:

        if request.args.get('login').isdigit() and check_password(int(request.args.get('login')), request.args.get('password')):
            # print('ip', request.remote_addr)
            token, role = making_token_for_session(int(request.args.get('login')), request.remote_addr, request.args.get('mac'))
            return('1~' + token + '~' + str(role[0]))
        else:
            return "0~"

        # except:
        #     return('0~')

    else:
        return '0~'


# Получение информации до записи на занятие
@app.route("/get/pre_lesson")
def pre_lesson():
    '''
    Отправить нужно 
    кинологов, 
    собак, 
    типы занятий, 
    площадки
    '''
    answer = ""
    # Получение кинологов
    sql = "SELECT id, name FROM staff WHERE role = 1"
    cursor = conn.cursor()
    cursor.execute(sql)
    handlers = cursor.fetchall()
    
    # Получение собак
    # sql = ("SELECT distinct dogs.id, dogs.name, breed, staff_id, places.id, places.name, phone FROM dogs JOIN places ON places.id = place_for_lesson " +
    # "JOIN users_dog on dog_id = dogs.id " +
    # "JOIN staff on user_id = staff.id " +  
    # "WHERE is_learning = true")

    sql = '''SELECT distinct on (dogs.id) dogs.id, dogs.name, breed, dogs.staff_id, places.id, places.name, phone, count(lesson.id), amount, dog_cours.id
        FROM dogs 
        JOIN places ON places.id = place_for_lesson 
        JOIN users_dog on dog_id = dogs.id 
        JOIN staff on user_id = staff.id 
        JOIN dog_cours on dog_cours.dog_id = dogs.id
        JOIN courses on courses.id = cours_id
        left JOIN lesson on lesson.dog_id = dogs.id and date >= date_of_cours
        WHERE is_learning = true
        group by dogs.id, dogs.name, places.id, breed, places.id, phone, user_id, amount, dog_cours.id
        ORDER BY dogs.id, dog_cours.id DESC'''
    cursor.execute(sql)
    dogs = cursor.fetchall()

    # Получение типов занятий
    sql = "SELECT id, name FROM types_of_lessons WHERE is_visible = true"
    cursor.execute(sql)
    types_of_lessons = cursor.fetchall()

    # Получение площадок
    sql = "SELECT id, name FROM places WHERE is_actual = true"
    cursor.execute(sql)
    places = cursor.fetchall()

    cursor.close()

    answer += "~"
    for i in handlers:
        answer += str(i[0]) + "|" + i[1] + "|"

    # print(result)
    answer += "~"
    for i in dogs:
        answer += str(i[0]) + "|" + i[1] + "|" + i[2] + "|" + str(i[3]) + "|"+ str(i[4]) + " " + i[5] + "|" + i[6] + "|" + str(i[7]) + "|" + str(i[8]) + "|"

    answer += "~"
    for i in types_of_lessons:
        answer += str(i[0]) + "|" + i[1] + "|"

    answer += "~"
    for i in places:
        answer += str(i[0]) + "|" + i[1] + "|"
        
    
    # print(answer)
    return '1' + answer


# Получение расписание кинолога
@app.route("/get/schedule")
def get_schedule():
    '''
    Возвращаю:
    id
    date
    dog_id, name
    type_id, name
    place_id, name
    onwer's phone
    '''
    if "id" not in request.args or "date" not in request.args:
        return "0~Введены не все поля"
    answer = ""
    # Получение кинологов
    sql = ("SELECT DISTINCT lesson.id, to_char(date, 'HH24:MI'), dogs.id, dogs.name, type_of_lesson, types_of_lessons.name, places.id, places.name, customer.phone FROM lesson " + 
    "JOIN types_of_lessons ON type_of_lesson = types_of_lessons.id " +
    "JOIN staff ON staff_id = staff.id " +
    "JOIN dogs ON dogs.id = dog_id " +
    "JOIN users_dog ON users_dog.dog_id = dogs.id " +
    "JOIN staff as customer ON customer.id = users_dog.user_id " +
    "JOIN places ON place_id = places.id " +
    " WHERE lesson.staff_id = %s and to_char(date, 'DD.MM.YYYY') = %s")
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get('id'), request.args.get('date')))
    schedule = cursor.fetchall()
    
    print(schedule)
    print(request.args.get('date'))
    # Проверим, есть ли расписание на день. Если нет, то предложим недельной давности
    date1 = datetime.strptime(request.args.get('date'), '%d.%m.%Y')
    if ( len(schedule) == 0 ) and date1 > datetime.today():
        date1 = (date1 - timedelta(7)).strftime("%d.%m.%Y")
        print('date',date1)
        cursor.execute(sql, (request.args.get('id'), date1))
        schedule = cursor.fetchall()
        print('schedule', schedule)

    cursor.close()
    
    
    for i in schedule:
        answer += "~" + str(i[0]) + "|" + i[1] + "|" + str(i[2]) + " " + i[3] + "|" + str(i[4]) + " " + i[5] + "|" + str(i[6]) + " " + i[7] + "|" + i[8]
    # print(answer)
    return '1' + answer


# Поиск Кинолога
@app.route("/get/handlers")
def get_handlers():
    sql = "SELECT id, name FROM staff WHERE role=1"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("phone"),))
    handlers = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = "~"
    for i in handlers:
        answer += str(i[0]) + "|" + i[1] + "|"    
    
    # print(answer)
    return '1' + answer


# Вычисление ЗП
@app.route("/get/salary")
def get_salary():
    if "date" not in request.args or "id" not in request.args:
        return "0~Введены не все поля"

    sql = "SELECT id, date, dog_id, type_of_lesson FROM lesson WHERE staff_id = %s AND to_char(date,'MM.YYYY') = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("id"),request.args.get("date")))
    result = cursor.fetchall()
    sql = "SELECT sum(for_instructor) FROM types_of_lessons JOIN lesson ON types_of_lessons.id = type_of_lesson WHERE staff_id = %s AND to_char(date,'MM.YYYY') = %s"
    cursor.execute(sql, (request.args.get("id"),request.args.get("date")))
    total_salary = cursor.fetchone()
    # print(total_salary)
    # print(sql)
    cursor.close()

    answer = "~"
    for i in result:
        answer += str(i[0]) + "|" + str(i[1]) + "|" + str(i[2]) + "|" + str(i[3]) + "|" 
    
    if total_salary[0] is None:
        answer += "~0"
    else: 
        answer += "~" + str(total_salary[0])
    # print(answer)
    return '1' + answer


# Поиск клиента
@app.route("/get/client")
def get_client():
    if "phone" not in request.args:
        return "0~Введены не все поля"
    if users_roles[request.args.get('token')] == 3:
        sql = "SELECT staff.id, name, phone, to_char(date_of_birth,'DD.MM.YYYY'), tg_id, \"e-mail\", role, \"user\".id FROM staff LEFT JOIN \"user\" ON staff_id = staff.id WHERE phone = %s"
    else:
        sql = "SELECT id, name, phone, to_char(date_of_birth,'DD.MM.YYYY'), tg_id, \"e-mail\", role, 'None' FROM staff WHERE phone = %s and role<2"
    
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("phone"),))
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    for i in result:
        answer += "~" + '|'.join(map(str, i))
        # answer += "~" + str(i[0]) + "|" + str(i[1]) + "|" + str(i[2]) + "|" + str(i[3]) + "|"+ str(i[4]) + "|" + str(i[5]) + "|" + str(i[6])
        
    
    # print(answer)
    return '1' + answer


# Поиск собак клиента
@app.route("/get/client/dog")
def get_clients_dog():
    if "id" not in request.args:
        return "0~Введены не все поля"
    
    # Если убрать distinct, то будет история посещения занятий полная
    # (в каком курсе сколько занятий проведено)
    sql = ("SELECT DISTINCT ON (dogs.id) dogs.id as id, dogs.name, dog_cours.id as cours_id, breed, amount, count(lesson.id) as was, place_for_lesson, dogs.staff_id " +
        "FROM users_dog " +
        "JOIN dogs ON dog_id = dogs.id JOIN dog_cours ON dogs.id = dog_cours.dog_id " +
        "JOIN courses ON cours_id = courses.id " +
        "LEFT JOIN lesson ON lesson.dog_id = dogs.id AND lesson.date > dog_cours.date_of_cours " +
        "WHERE user_id = %s " +
        "group by dogs.id, dog_cours.id, amount " +
        "ORDER BY dogs.id, dog_cours.id DESC")
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("id"),))
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    for i in result:
        answer += "~" + str(i[0]) + "|" + str(i[1]) + "|" + str(i[3]) + "|"+ str(i[4]) + "|" + str(i[5]) + "|" + str(i[6]) + "|" + str(i[7])
    
    # print(answer)
    return '1' + answer


# Поиск собак клиента
@app.route("/get/dog/client")
def get_dog_clients():
    if "dog_id" not in request.args:
        return "0~Введены не все поля"
    
    # 
    sql = ("SELECT staff.id, name, phone, to_char(date_of_birth,'DD.MM.YYYY'), tg_id, \"e-mail\", role FROM staff JOIN users_dog ON staff.id = user_id WHERE dog_id = %s")
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("dog_id"),))
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    for i in result:
        answer += "~" + str(i[0]) + "|" + str(i[1]) + "|" + str(i[2]) + "|" + str(i[3]) + "|"+ str(i[4]) + "|" + str(i[5]) + "|" + str(i[6])
    
    # print(answer)
    return '1' + answer


# Получение инофрмации до создания собаки (возможные абонементы и прочее)
@app.route("/get/pre_dogs")
def get_pre_dogs():
    # Если редактирование собаки, то 1.1
    # Если просто информация до создания собак, то 1
    if "dog_id" in request.args:
        answer = "1.1~"
    else:
        answer = "1~"
    # Получаем курсы
    sql = "SELECT id, name, amount, price FROM courses WHERE is_actual = True"
    cursor = conn.cursor()
    cursor.execute(sql)
    courses = cursor.fetchall()
    
    # Получаем площадки 
    sql = "SELECT id, name FROM places WHERE is_actual = True"
    cursor.execute(sql)
    places = cursor.fetchall()
    
    # Получаем кинологов
    sql = "SELECT id, name FROM staff WHERE role = 1"
    cursor.execute(sql)
    staff = cursor.fetchall()
    
    # Получаем информацию о собаке
    dog_info = ""
    if "dog_id" in request.args:
        sql = "SELECT dogs.id, name, breed, staff_id, place_for_lesson, cours_id, is_learning FROM dogs JOIN dog_cours ON dog_id = dogs.id WHERE dogs.id = %s ORDER BY date_of_cours DESC"
        cursor.execute(sql, (request.args.get("dog_id"),))
        dog_info = cursor.fetchone()
        # print(dog_info)
    cursor.close()
    
    # print(courses)
    # print(places)
    # print(staff)
    staff_index = " "
    cours_index = " "
    place_index = " "
    # print("dog_info",dog_info)
    # print("courses",courses)
    for i in courses:
        answer += "|" + str(i[0]) + "@" + str(i[1]) + "@" + str(i[2]) + "@" + str(i[3])
        # Если пришло id собаки, то ищем в отправляемом нужный id
        if dog_info != "" and i[0] == dog_info[5]:
            cours_index = courses.index(i)
    answer += "~"

    for i in places:
        answer += "|" + str(i[0]) + " " + str(i[1])
        if dog_info != "" and i[0] == dog_info[4]:
            place_index = places.index(i)
    answer += "~"

    for i in staff:
        answer += "|" + str(i[0]) + " " + str(i[1])
        if dog_info != "" and i[0] == dog_info[3]:
            staff_index = staff.index(i)

    if "dog_id" in request.args: 
        answer += "~" + str(cours_index) + "|" + str(place_index) + "|" + str(staff_index)
        answer += "|" + str(dog_info[1]) + "|" + str(dog_info[2]) + "|" + str(dog_info[6])
    # print(staff_index, cours_index, place_index)
    
    return answer


# Поиск курсов
@app.route("/get/courses")
def get_courses():
    # Получаем все курсы
    sql = "SELECT id, name, amount, price, is_actual FROM courses "
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    # Формируем ответ
    for i in result:
        answer += "~" + str(i[0]) + "|" + str(i[1]) + "|" + str(i[2]) + "|" + str(i[3]) + "|" + str(i[4])
        
    
    # print(answer)
    return '1' + answer


# Поиск площадок
@app.route("/get/places")
def get_places():
    # Получаем все курсы
    sql = "SELECT id, address, name, is_actual FROM places "
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    # Формируем ответ
    for i in result:
        answer += "~" + str(i[0]) + "|" + i[1] + "|" + i[2] + "|" + str(i[3])
        
    # print(answer)
    return '1' + answer


# Поиск объявлениz
@app.route("/get/advertisement")
def get_advertisement():
    if "id" not in request.args:
        return "0~Нет id"
    
    # Получаем все курсы
    sql = "SELECT id, to_char(date_to_post,'DD.MM.YYYY'), sed_to, text FROM advertisement WHERE id = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("id"),))
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    # Формируем ответ
    for i in result:
        answer += "~" + str(i[0]) + "~" + i[1] + "~" + i[2] + "~" + i[3]
        
    
    # print(answer)
    return '1' + answer


# Поиск объявлений
@app.route("/get/ad")
def get_ad():
    # Получаем все курсы
    sql = "SELECT id, to_char(date_to_post,'DD.MM.YYYY'), sed_to, created_by FROM advertisement "
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    # Формируем ответ
    for i in result:
        answer += "~" + str(i[0]) + "|" + i[1] + "|" + i[2] + "|" + str(i[3])
        
    
    # print(answer)
    return '1' + answer


# Добавление собаки клиента
@app.route("/add/dog/client")
def add_dog_client():
    # Проверка на все аргументы
    if ('dog_id' not in request.args or 'id' not in request.args):
        return '0~Введены не все поля'
    answer = "0~"

    # Проверяем, существует ли такая связь
    sql = "SELECT count(*) from users_dog WHERE dog_id = %s AND user_id = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("dog_id"), request.args.get("id") ))
    amount = cursor.fetchone()
    print(amount)

    # Если связи нет, то добавляем
    if amount[0] == 0:
        sql = "INSERT INTO users_dog VALUES (DEFAULT, %s, %s)"
        cursor.execute(sql, (request.args.get("id"), request.args.get("dog_id") ))
        conn.commit()
        answer = "1~"
    cursor.close()
    
    return answer


# Добавление собаки курса
@app.route("/add/dog/cours")
def add_dog_cours():
    # Проверка на все аргументы
    if ('dog_id' not in request.args or 'cours_id' not in request.args):
        return '0~Введены не все поля'
    answer = "1~"

    # Проверяем, существует ли такая связь
    sql = "INSERT INTO dog_cours (dog_id, cours_id, date_of_cours) VALUES (%s, %s, %s)"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("dog_id"), request.args.get("cours_id"), date.today() ))
    conn.commit()
    cursor.close()
    
    return answer


# Создание новой собаки
@app.route("/new/dog")
def new_dog():
    '''
    Создание новой собаки.
    Получаю 
    '''

    if ('name' not in request.args or 'usr_id' not in request.args or 
            'breed' not in request.args or 'staff_id' not in request.args or 
            'place' not in request.args or 'cours' not in request.args or
            'actual' not in request.args):
        return '0~Введены не все поля'
    staff_id = request.args.get("staff_id")
    if staff_id == "None":
        staff_id = None

    cursor = conn.cursor()
    if "dog_id" in request.args:
        sql = "UPDATE dogs SET name = %s, breed = %s, staff_id = %s, place_for_lesson = %s, is_learning = %s WHERE id = %s"
        cursor.execute(sql, (request.args.get("name"), request.args.get("breed"), 
            staff_id, request.args.get("place"), request.args.get("actual"), request.args.get("dog_id")))
        sql = "UPDATE dog_cours SET cours_id = %s WHERE id = (SELECT id from dog_cours WHERE dog_id = %s ORDER BY id DESC LIMIT 1)"
        cursor.execute(sql, (request.args.get("cours"), request.args.get("dog_id")))
    else:
        sql = 'INSERT INTO dogs (name, breed, is_learning, staff_id, place_for_lesson) VALUES (%s, %s, %s, %s, %s) RETURNING id'
        cursor.execute(sql, (request.args.get("name"), request.args.get("breed"),
            request.args.get('actual'), staff_id, request.args.get("place")))
        dog_id = cursor.fetchone()
        print(dog_id)
        sql = "INSERT INTO users_dog (user_id, dog_id) VALUES (%s, %s)"
        cursor.execute(sql, (request.args.get("usr_id"), dog_id[0]))
        sql = "INSERT INTO dog_cours (dog_id, cours_id, date_of_cours) VALUES (%s, %s, %s)"
        cursor.execute(sql, (dog_id, request.args.get("cours"), date.today() ))
    conn.commit()
    cursor.close()
    
    return "1~"


# Создание нового клиента
@app.route("/new/client")
def new_clietn():
    '''
    Создание нового клиента
    От пользователя получаем Имя, Телефон, Дату рождения, Тг ид, Почту, Роль
    '''
    answer = "1~"
    if ('name' not in request.args or 'phone' not in request.args or 
            'birth' not in request.args or 'tg_id' not in request.args or 
            'email' not in request.args or 'role' not in request.args):
        return '0~Введены не все поля'

    if request.args.get("role") == "2" and users_roles[request.args.get("token")] != 3:
        return "0~Попытка создать админа без соответствующих полномочий"
    
    sql = 'INSERT INTO staff (name, role, phone, date_of_birth, tg_id, "e-mail") VALUES (%s, %s, %s, %s, %s, %s) RETURNING id'
    

    # Тут проверка на нуллы
    # Если Null, то запомним как None
    birth = request.args.get("birth")
    tg_id = request.args.get("tg_id")
    if request.args.get("birth") == "Null":
        birth = None
    if request.args.get("tg_id") == "Null":
        tg_id = None
    
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("name"), request.args.get("role"), request.args.get("phone"), birth, tg_id, request.args.get("email")))
    staff_id = cursor.fetchone()
    conn.commit()
    if request.args.get("role") == "2":
        sql = "INSERT INTO \"user\" (password, staff_id) VALUES (%s, %s) RETURNING id"
        cursor.execute(sql, (making_hash(request.args.get("password")), staff_id[0]))
        staff_id = cursor.fetchone()[0]
        answer += str(staff_id)
    conn.commit()
    cursor.close()
    
    return answer


# Создание нового курса
@app.route("/new/cours")
def new_cours():
    '''
    Создание нового курса
    От пользователя получаем название, кол-во, цена, актуальность, ?id
    '''

    if ('name' not in request.args or 'amount' not in request.args or 
            'price' not in request.args or 'actual' not in request.args):
        return '0~Введены не все поля'
    
    if 'id' in request.args:
        sql = 'UPDATE courses SET name=%s, amount=%s, price=%s, is_actual=%s WHERE id=%s'
        to_sql = (request.args.get('name'), request.args.get('amount'), request.args.get('price'), request.args.get('actual'), request.args.get('id') )
    else:
        sql = "INSERT INTO courses (name, amount, price, is_actual) VALUES (%s, %s, %s, %s)"
        to_sql = (request.args.get('name'), request.args.get('amount'), request.args.get('price'), request.args.get('is_actual'))
    
    cursor = conn.cursor()
    cursor.execute(sql, to_sql)
    conn.commit()
    cursor.close()
    
    return "1~"


# Создание новой площадки
@app.route("/new/place")
def new_place():
    '''
    Создание новой площадки
    От пользователя получаем адрес, название, актуальность, ?id
    '''

    if ('name' not in request.args or 
            'address' not in request.args or 'actual' not in request.args):
        return '0~Введены не все поля'
    
    if 'id' in request.args:
        sql = 'UPDATE places SET name=%s, address=%s,  is_actual=%s WHERE id=%s'
        to_sql = (request.args.get('name'), request.args.get('address'), request.args.get('actual'), request.args.get('id') )
    else:
        sql = "INSERT INTO places (name, address, is_actual) VALUES (%s, %s, %s)"
        to_sql = (request.args.get('name'), request.args.get('address'), request.args.get('is_actual'))
    
    cursor = conn.cursor()
    cursor.execute(sql, to_sql)
    conn.commit()
    cursor.close()
    
    return "1~"


# Создание новой рассылки
@app.route("/new/ad")
def new_ad():
    '''
    Создание новой рассылки
    От пользователя получаем текст, кому слать, когда слать, ?id
    '''
    # Проверка
    if ('text' not in request.args or 'send_to' not in request.args or
            'created_by' not in request.args or 'date' not in request.args):
        return '0~Введены не все поля'
    if request.args.get('send_to') == "":
        send_to = "None"
    else:
        send_to = request.args.get('send_to')

    if 'id' in request.args:
        sql = 'UPDATE advertisement SET text=%s, sed_to=%s,  created_by=%s, date_to_post=%s WHERE id=%s'
        to_sql = (request.args.get('text'), send_to, request.args.get('created_by'), 
                request.args.get('date'), request.args.get('id') )
    else:
        sql = "INSERT INTO advertisement (text, sed_to, date_to_post, created_by) VALUES (%s, %s, %s, %s)"
        to_sql = (request.args.get('text'), send_to, 
                request.args.get('date'), request.args.get('created_by'))
    print(sql)
    cursor = conn.cursor()
    cursor.execute(sql, to_sql)
    conn.commit()
    cursor.close()
    
    return "1~"


# Редактирование клиента
@app.route("/edit/client")
def edit_client():
    answer = ""
    if ('name' not in request.args or 'phone' not in request.args or 
            'birth' not in request.args or 'tg_id' not in request.args or 
            'email' not in request.args or 'id' not in request.args or
            'role' not in request.args):
        return '0~Введены не все поля'
    # Если создаём админа не с главного админа
    if request.args.get("role") == "2" and users_roles[request.args.get("token")] != 3:
        return "0~Попытка создать админа без соответствующих полномочий"
    # Будем обновлять пользователя
    sql = 'UPDATE staff SET name = %s, role = %s, phone= %s, date_of_birth = %s, tg_id= %s, "e-mail" = %s WHERE id = %s RETURNING id'

    # Тут проверка на нуллы
    # Если Null, то запомним как None
    birth = request.args.get("birth")
    tg_id = request.args.get("tg_id")
    if request.args.get("birth") == "Null":
        birth = None
    if request.args.get("tg_id") == "Null":
        tg_id = None
    # Выполняем sql код    
    cursor = conn.cursor()
    cursor.execute(sql, (
        request.args.get("name"), request.args.get("role"),
        request.args.get("phone"), birth, tg_id, request.args.get("email"),
        request.args.get("id") ))

    staff_id = cursor.fetchone()
    conn.commit()
    
    # Узнаём, есть ли аккаунт (логин+пароль) у изменяемого пользователя
    sql = "SELECT count(*) FROM \"user\" WHERE staff_id = %s"
    cursor.execute(sql, (staff_id[0],))
    count_of_users = cursor.fetchone()

    # Если создаём админа
    if request.args.get("role") == "2":
        # Если аккаунт есть, его меняем
        # Иначе создаём
        if count_of_users[0] == 1:
            sql = "UPDATE \"user\" SET password = %s WHERE staff_id = %s"
            cursor.execute(sql, (making_hash(request.args.get("password")), staff_id[0]))
        else:
            sql = "INSERT INTO \"user\" (password, staff_id) VALUES (%s, %s) RETURNING id"
            cursor.execute(sql, (making_hash(request.args.get("password")), staff_id[0]))
            staff_id = cursor.fetchone()
            answer = str(staff_id[0])
        conn.commit()
    # Если создаём не админа и есть аккаунт, то удалим аккаунт
    elif count_of_users[0] != 0:
        sql = "SELECT token FROM sessions WHERE user_id = (SELECT id FROM \"user\" WHERE staff_id=%s limit 1) and token != ''"
        cursor.execute(sql, (staff_id[0],))
        id_to_delete = cursor.fetchone()
        print(id_to_delete)
        if (id_to_delete is not None) and id_to_delete in users_roles:
            users_roles.pop(id_to_delete[0])
        sql = "DELETE FROM \"user\" WHERE staff_id = %s"
        cursor.execute(sql, (staff_id[0],))
        conn.commit()
    

    cursor.close()
    
    return "1~" + answer


# Редактирование расписания
@app.route("/edit/schedule")
def edit_schedule():
    if ('args' not in request.args):
        return '0~Введены не все поля'
    # Список со значенияим
    to_edit = request.args.get("args").split("|")
    to_edit.pop(-1)

    sql = ""
    if request.args.get("args")[0] != ".":
        sql = "INSERT INTO lesson (date, dog_id, place_id, type_of_lesson, staff_id) VALUES (to_timestamp(%s, 'HH24:MI DD.MM.YYYY'), %s, %s, %s, %s)"
        for i in range(int((len(to_edit))/5 - 1)):
            sql += ",(to_timestamp(%s, 'HH24:MI DD.MM.YYYY'), %s, %s, %s, %s)"
    sql_pre = "DELETE FROM lesson WHERE to_char(date, 'DD.MM.YYYY') = %s and staff_id = %s"
    
    # print(tuple(to_edit))
    # print(sql)

    cursor = conn.cursor()
    # print(to_edit[0].split())
    cursor.execute(sql_pre, (to_edit[0].split()[1], to_edit[4]) )
    if sql != "":
        cursor.execute(sql, tuple(to_edit))
    conn.commit()
    cursor.close()
    
    return "1~"


# Удаление хозяина у человека
@app.route("/delete/dog/client")
def delete_dog_client():
    # Проверка на параметры
    if ('dog_id' not in request.args or 'id' not in request.args):
        return '0~Введены не все поля'

    # Узнаём, последний ли хозяин
    sql = "SELECT count(*) FROM users_dog WHERE dog_id = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("dog_id") ,))
    amount = cursor.fetchone()

    answer = "0~"
    print(amount)
    # Проверка на удаление последнего хозяина
    if amount[0] != 1:
        sql = "DELETE FROM users_dog WHERE dog_id = %s and user_id = %s"
        cursor.execute(sql, (request.args.get("dog_id"), request.args.get("id") ))
        conn.commit()
        answer = "1~"
    cursor.close()

    return answer


# Приём бд
@app.route("/upload/database", methods=['POST'])
def new_database():
    # Если гл. админ
    if users_roles[request.args.get('token')] == 3:
        print(request.files)
        # Загружаем файл
        file = request.files['file']
        file.save("./DB.sql")
        cursor = conn.cursor()
        try:
            load(cursor)
        except psycopg2.errors.SyntaxError:
            conn.rollback()
        conn.commit()
        cursor.close()
        conn.close()
        # Удаляем файд с БД
        os.remove('./table_dump.sql')
        # Заново запускаем программу
        main()
        return "1~"
    else:
        return "0~"


def main():
    ### Подключение к БД 
    global conn, users_roles
    conf = ''
    # Читаю из файла пароли логины
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


    

    ### Словарь для ролей
    cursor = conn.cursor()
    sql = "SELECT token, role FROM sessions JOIN \"user\" ON  \"user\".id = user_id JOIN staff ON staff.id = staff_id where token!='' "
    cursor.execute(sql)
    place_for_roles_before_main = cursor.fetchall()
    for i in place_for_roles_before_main:
        users_roles[i[0]] = i[1]
    print(users_roles)
    # dumb(cursor)
    cursor.close()


if __name__ == "__main__":
    conn = None
    users_roles = {}
    main()
    app.run(debug=True)