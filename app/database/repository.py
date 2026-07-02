import sqlite3
from datetime import datetime

from app.models.article import Article
from config.settings import DATABASE_PATH, DATA_DIR


class ArticleRepository:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.conn.cursor()

        self.create_table()

    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT,
            link TEXT UNIQUE,
            source TEXT,
            published TEXT,

            content TEXT,
            cleaned_content TEXT,

            score INTEGER DEFAULT 0,

            summary TEXT,
            script TEXT,
            thumbnail TEXT,

            status TEXT DEFAULT 'COLLECTED',

            created_at TEXT,
            updated_at TEXT
        )
        """)

        self.conn.commit()

    def save(self, article: Article):
        try:
            now = datetime.now().isoformat()

            self.cursor.execute("""
            INSERT INTO articles (
                title, link, source, published,
                content, cleaned_content,
                score,
                summary, script, thumbnail,
                status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.title,
                article.link,
                article.source,
                article.published,
                article.content,
                article.cleaned_content,
                article.score,
                article.summary,
                article.script,
                article.thumbnail,
                article.status,
                now,
                now
            ))

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            return False

    def update_article(self, article: Article):
        self.cursor.execute("""
        UPDATE articles
        SET
            content = ?,
            cleaned_content = ?,
            score = ?,
            summary = ?,
            script = ?,
            thumbnail = ?,
            status = ?,
            updated_at = ?
        WHERE link = ?
        """, (
            article.content,
            article.cleaned_content,
            article.score,
            article.summary,
            article.script,
            article.thumbnail,
            article.status,
            datetime.now().isoformat(),
            article.link
        ))

        self.conn.commit()

    def get_unprocessed(self, limit=10):
        self.cursor.execute("""
        SELECT title, link, source, published,
               content, cleaned_content,
               score, summary, script, thumbnail,
               status
        FROM articles
        WHERE status NOT IN ('DONE', 'FAILED')
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = self.cursor.fetchall()
        articles = []

        for row in rows:
            articles.append(Article(
                title=row[0],
                link=row[1],
                source=row[2],
                published=row[3],
                content=row[4] or "",
                cleaned_content=row[5] or "",
                score=row[6] or 0,
                summary=row[7] or "",
                script=row[8] or "",
                thumbnail=row[9] or "",
                status=row[10] or "COLLECTED"
            ))

        return articles

    def close(self):
        self.conn.close()