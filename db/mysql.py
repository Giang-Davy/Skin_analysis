import mysql.connector

# Connection on MySQL (the local)
def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Gkc19Dur!!!!",
        database="user_db"
    )
    return conn
