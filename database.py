import os
import aiosqlite
from datetime import datetime


DB_PATH = os.getenv("DB_PATH", "food_diary.db")


# ============================================================
# HELPERS
# ============================================================

def today_date():
    return datetime.now().strftime("%Y-%m-%d")


# ============================================================
# INIT DATABASE
# ============================================================

async def init_db():

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                calories_goal REAL DEFAULT 0,
                protein_goal REAL DEFAULT 0,
                fat_goal REAL DEFAULT 0,
                carbs_goal REAL DEFAULT 0
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                calories REAL DEFAULT 0,
                protein REAL DEFAULT 0,
                fat REAL DEFAULT 0,
                carbs REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                amount_unit TEXT DEFAULT 'г',
                created_at TEXT NOT NULL
            )
            """
        )

        # Отдельная таблица для протеина.
        # Благодаря дате счётчик автоматически новый каждый день.
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS protein_shakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                shake_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        await db.commit()


# ============================================================
# USERS
# ============================================================

async def create_user(
    telegram_id: int
):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO users (
                telegram_id,
                calories_goal,
                protein_goal,
                fat_goal,
                carbs_goal
            )
            VALUES (?, 0, 0, 0, 0)
            """,
            (telegram_id,)
        )

        await db.commit()


async def get_user(
    telegram_id: int
):

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        row = await cursor.fetchone()

        if not row:
            return None

        return dict(row)


async def update_user_goals(
    telegram_id: int,
    calories: float,
    protein: float,
    fat: float,
    carbs: float
):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE users
            SET
                calories_goal = ?,
                protein_goal = ?,
                fat_goal = ?,
                carbs_goal = ?
            WHERE telegram_id = ?
            """,
            (
                calories,
                protein,
                fat,
                carbs,
                telegram_id
            )
        )

        await db.commit()


# ============================================================
# PROTEIN SHAKES
# ============================================================

async def get_today_protein_shakes(
    telegram_id: int
) -> int:

    today = today_date()

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM protein_shakes
            WHERE telegram_id = ?
            AND shake_date = ?
            """,
            (
                telegram_id,
                today
            )
        )

        row = await cursor.fetchone()

        if not row:
            return 0

        return min(int(row[0] or 0), 2)


async def add_protein_shake(
    telegram_id: int
) -> bool:

    today = today_date()

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM protein_shakes
            WHERE telegram_id = ?
            AND shake_date = ?
            """,
            (
                telegram_id,
                today
            )
        )

        row = await cursor.fetchone()

        current = int(row[0] or 0)

        # Максимум 2 стакана в день
        if current >= 2:
            return False

        await db.execute(
            """
            INSERT INTO protein_shakes (
                telegram_id,
                shake_date,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                telegram_id,
                today,
                datetime.now().isoformat()
            )
        )

        await db.commit()

        return True


# ============================================================
# MEALS
# ============================================================

async def add_meal(
    telegram_id: int,
    name: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
    amount: float,
    amount_unit: str
):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO meals (
                telegram_id,
                name,
                calories,
                protein,
                fat,
                carbs,
                amount,
                amount_unit,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                name,
                calories,
                protein,
                fat,
                carbs,
                amount,
                amount_unit,
                datetime.now().isoformat()
            )
        )

        await db.commit()


async def get_today_meals(
    telegram_id: int
):

    today = today_date()

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM meals
            WHERE telegram_id = ?
            AND date(created_at) = ?
            ORDER BY id ASC
            """,
            (
                telegram_id,
                today
            )
        )

        rows = await cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ============================================================
# TODAY TOTALS
# ============================================================

async def get_today_totals(
    telegram_id: int
):

    today = today_date()

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT
                COALESCE(SUM(calories), 0),
                COALESCE(SUM(protein), 0),
                COALESCE(SUM(fat), 0),
                COALESCE(SUM(carbs), 0)
            FROM meals
            WHERE telegram_id = ?
            AND date(created_at) = ?
            """,
            (
                telegram_id,
                today
            )
        )

        row = await cursor.fetchone()

        calories = float(row[0] or 0)
        protein = float(row[1] or 0)
        fat = float(row[2] or 0)
        carbs = float(row[3] or 0)

        # ====================================================
        # PROTEIN SHAKES
        # ====================================================

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM protein_shakes
            WHERE telegram_id = ?
            AND shake_date = ?
            """,
            (
                telegram_id,
                today
            )
        )

        protein_row = await cursor.fetchone()

        protein_shakes = 0

        if protein_row:
            protein_shakes = min(
                int(protein_row[0] or 0),
                2
            )

        # Один стакан = 50 г белка
        protein += protein_shakes * 50

        return {
            "calories": calories,
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        }


# ============================================================
# DELETE LAST MEAL
# ============================================================

async def delete_last_meal(
    telegram_id: int
) -> bool:

    today = today_date()

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT id
            FROM meals
            WHERE telegram_id = ?
            AND date(created_at) = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                telegram_id,
                today
            )
        )

        row = await cursor.fetchone()

        if not row:
            return False

        await db.execute(
            """
            DELETE FROM meals
            WHERE id = ?
            """,
            (row[0],)
        )

        await db.commit()

        return True
