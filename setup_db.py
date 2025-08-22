"""
Author: Ashwin Nair
Date: 2025-08-22
Project name: setup_db.py
Summary: Enter summary here.
"""

import sqlite3

conn = sqlite3.connect("anime_manga.db")
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    discord_id INTEGER UNIQUE NOT NULL,
    display_name TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS anime (
    anime_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE NOT NULL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS manga (
    manga_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE NOT NULL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS user_library (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    media_type TEXT CHECK(media_type IN ('anime','manga')) NOT NULL,
    media_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('completed','reading','dropped','planned')) NOT NULL DEFAULT 'completed',
    rating INTEGER CHECK(rating >= 0 AND rating <= 10),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)""")

conn.commit()
conn.close()

print("✅ Database initialized!")

