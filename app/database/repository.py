import sqlite3
from pathlib import Path
from datetime import datetime

from app.models.article import Article


class ArticleRepository:

    def __init__(self):

        Path("data").mkdir(exist_ok=True)

        self.conn = sqlite3.connect("data/articles.db")
        self.cursor = self.conn.cursor()

        self.create_table()

    def create_table(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            url TEXT UNIQUE,

            source TEXT,

            published TEXT,

            collected_at TEXT

        )
        """)

        self.conn.commit()

    def save(self, article: Article):

        try:

            self.cursor.execute("""

            INSERT INTO articles
            (title, url, source, published, collected_at)

            VALUES (?, ?, ?, ?, ?)

            """, (

                article.title,
                article.link,
                article.source,
                article.published,
                datetime.now().isoformat()

            ))

            self.conn.commit()

            return True

        except sqlite3.IntegrityError:

            return False

    def close(self):

        self.conn.close()