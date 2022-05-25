def load(cursor):
    table_names = [
        "staff", "\"user\"", "advertisement", 
        "courses", "places", "dogs", "dog_cours", 
        "types_of_lessons", "users_dog", 
        "sessions", "lesson" ]  # place your table name here
    
    for i in reversed(table_names):
        sql = "DELETE FROM " + i
        cursor.execute(sql)

    with open("DB.sql", "r") as f:
        for line in f:
            cursor.execute(line)


     

         
              
            
            
          
             
  
              
         