import psycopg2
from datetime import date, datetime, timedelta
### Подключение к БД 
# conf = ''
# Читаю из файла пароли логины

# with open('conf.txt', 'r') as f:
#     conf = f.read()
# conf = conf.split('~')
# conn = psycopg2.connect(dbname=conf[0], user=conf[1],
#                         password=conf[2], host=conf[3])
# conn = psycopg2.connect("dbname=test user=postgres")  # change this according to your RDBMS configuration
# cursor = conn.cursor()
def dumb(cursor):
    table_names = [
        "staff", "\"user\"", "advertisement", 
        "courses", "places", "dogs", "dog_cours", 
        "types_of_lessons", "users_dog", 
        "sessions", "lesson" ]  # place your table name here
    
    with open("table_dump.sql", "w") as f:
        for table_name in table_names:
            cursor.execute("SELECT * FROM %s" % (table_name))  # change the query according to your needs
            column_names = []
            columns_descr = cursor.description
            for c in columns_descr:
                column_names.append(c[0])
            insert_prefix = 'INSERT INTO %s (%s) VALUES ' % (table_name, ', '.join(column_names))
            rows = cursor.fetchall()
            for row in rows:
                row_data = []
                for rd in row:
                    if rd is None:
                        row_data.append('NULL')
                    elif isinstance(rd, datetime):
                        row_data.append("'%s'" % (rd.strftime('%Y-%m-%d %H:%M:%S') ))
                    else:
                        row_data.append(repr(rd))
                f.write('%s (%s);\n' % (insert_prefix, ', '.join(row_data)))  # this is the text that will be put in the SQL file. You can change it if you wish.


     

         
              
            
            
          
             
  
              
         