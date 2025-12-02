import sqlite3
from fastapi import FastAPI
from faker import Faker

app = FastAPI()
fake = Faker()
DB_PATH = "/data/database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        address TEXT,
        age INTEGER
    )
    ''')
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        users = [(fake.name(), fake.email(), fake.address(), fake.random_int(18, 80)) for _ in range(10)]
        cursor.executemany('INSERT INTO users (name, email, address, age) VALUES (?, ?, ?, ?)', users)
        conn.commit()
    conn.close()

init_db()

@app.get("/users")
def get_users(limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users LIMIT ?', (limit,))
    data = cursor.fetchall()
    conn.close()
    return {"users": data}
