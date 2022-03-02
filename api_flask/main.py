from flask import Flask, request, g
import hashlib
import uuid
import psycopg2
import time
from datetime import date

'''
TO DO

На вкладке с курсами скрыть неактуальные combobox
Создать изменить курс, площадку
Запретить вводить &?
Добавить гифку на время ожидания на клиент
Отдельный декоратор для админа

'''

### Подключение к БД 
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


app = Flask(__name__)

def making_hash(password: str):
    # Тут создаю хэш для нового пароля с солью
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt
    

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
    if len(user_info) == 0:
        return False
    # user_info: id (login); password; staff_id (user's id, who own this pass)
    password, salt = user_info[1].split(':')
    return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
    
def making_token_for_session(login: int, ip: str, mac: str):
    ctime = time.time()
    token = uuid.uuid4().hex
    sql = "UPDATE sessions SET token = '' WHERE user_id = %s AND token != ''"
    cursor = conn.cursor()
    cursor.execute(sql,(login,))
    conn.commit()
    sql = "INSERT INTO sessions(user_id, token, time, ip, mac) VALUES(%s,%s,%s,%s,%s)"
    cursor.execute(sql,(login, str(ctime)+token , ctime, ip, mac))
    conn.commit()
    sql = "SELECT role FROM staff JOIN \"user\" ON staff_id = staff.id WHERE \"user\".id = %s"
    cursor.execute(sql, (login,))
    role = cursor.fetchone()
    cursor.close()
    return str(ctime) + token, role 


# Auth check
@app.before_request
def before_request():
    # Если пользователь авторизуется, то нет смысла проверять его сессию
    if request.path == "/login":
        return 
    # Если нет в запросе логина мака токена
    elif "token" not in request.args or "mac" not in request.args or "login" not in request.args:
        # Заставляем переавторизироваться
        return "-1~"
    
    # Получаем информацию о сессии пользователя с конкретным токеном и мак 
    sql = "SELECT * FROM sessions WHERE user_id=%s AND token=%s AND mac=%s"
    cursor = conn.cursor();
    cursor.execute(sql,(request.args.get("login"), request.args.get("token"), request.args.get("mac")))
    user = cursor.fetchone()
    cursor.close()
    
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
        token, role = making_token_for_session(request.args.get("login"), request.remote_addr, request.args.get("mac"))
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
        try:

            if check_password(int(request.args.get('login')), request.args.get('password')):
                # print('ip', request.remote_addr)
                token, role = making_token_for_session(int(request.args.get('login')), request.remote_addr, request.args.get('mac'))
                return('1~' + token + '~' + str(role[0]))
            else:
                return "0~"

        except:
            return('0~')

    else:
        return '0~'

# Поиск клиента
@app.route("/get/client")
def get_client():
    if "phone" not in request.args:
        return "0~Введены не все поля"
    sql = "SELECT id, name, phone, to_char(date_of_birth,'DD.MM.YYYY'), tg_id, \"e-mail\", role FROM staff WHERE phone = %s and role<2"
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("phone"),))
    result = cursor.fetchall()
    cursor.close()

    # print(result)
    answer = ""
    for i in result:
        answer += "~" + str(i[0]) + "|" + str(i[1]) + "|" + str(i[2]) + "|" + str(i[3]) + "|"+ str(i[4]) + "|" + str(i[5]) + "|" + str(i[6])
        
    
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
    sql = "SELECT id, name, amount, price FROM courses"
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

    for i in courses:
        answer += "|" + str(i[0]) + " " + str(i[1]) + " " + str(i[2]) + " " + str(i[3])
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

# Поиск клиента
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

# Добавление собаки клиента
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

# Создание нового клиента
@app.route("/new/client")
def new_clietn():
    '''
    Создание нового клиента
    От пользователя получаем Имя, Телефон, Дату рождения, Тг ид, Почту, Роль
    '''

    if ('name' not in request.args or 'phone' not in request.args or 
            'birth' not in request.args or 'tg_id' not in request.args or 
            'email' not in request.args or 'role' not in request.args):
        return '0~Введены не все поля'
    sql = 'INSERT INTO staff (name, role, phone, date_of_birth, tg_id, "e-mail") VALUES (%s, %s, %s, %s, %s, %s)'
    

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
    conn.commit()
    cursor.close()
    
    return "1~"

# Создание нового клиента
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

# Редактирование клиента
@app.route("/edit/client")
def edit_client():
    if ('name' not in request.args or 'phone' not in request.args or 
            'birth' not in request.args or 'tg_id' not in request.args or 
            'email' not in request.args or 'id' not in request.args or
            'role' not in request.args):
        return '0~Введены не все поля'
    sql = 'UPDATE staff SET name = %s, role = %s, phone= %s, date_of_birth = %s, tg_id= %s, "e-mail" = %s WHERE id = %s'
    

    # Тут проверка на нуллы
    # Если Null, то запомним как None
    birth = request.args.get("birth")
    tg_id = request.args.get("tg_id")
    if request.args.get("birth") == "Null":
        birth = None
    if request.args.get("tg_id") == "Null":
        tg_id = None
        
    cursor = conn.cursor()
    cursor.execute(sql, (request.args.get("name"), request.args.get("role"), request.args.get("phone"), birth, tg_id, request.args.get("email"), request.args.get("id") ))
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



if __name__ == "__main__":
    app.run(debug=True)