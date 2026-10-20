import aiosqlite

DB_NAME = "giveaway.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                prize TEXT,
                screenshots_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'new'
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT prize, screenshots_count, status FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def update_user(user_id, **kwargs):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        for key, value in kwargs.items():
            await db.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()
