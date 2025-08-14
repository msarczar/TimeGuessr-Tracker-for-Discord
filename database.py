import sqlite3
import os

DATABASE_NAME = 'timeguessr_scores.db'

def connect_db():
    return sqlite3.connect(DATABASE_NAME)

def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            game_date TEXT NOT NULL,
            score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            game_number INTEGER,
            message_id TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized or already exists.")

def add_score(player_id, player_name, game_date, score, max_score, game_number, message_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO scores (player_id, player_name, game_date, score, max_score, game_number, message_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (player_id, player_name, game_date, score, max_score, game_number, message_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        print(f"Duplicate entry: Message ID {message_id} already recorded.")
        conn.close()
        return False
    except Exception as e:
        print(f"Error adding score: {e}")
        conn.close()
        return False

def get_scores(start_date=None, end_date=None, player_id=None):
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT player_id, player_name, score, game_date FROM scores"
    params = []
    conditions = []

    if start_date:
        conditions.append("game_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("game_date <= ?")
        params.append(end_date)
    if player_id:
        conditions.append("player_id = ?")
        params.append(player_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY game_date ASC, score DESC" # Order for consistent results when processing streaks

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()
    conn.close()
    return results