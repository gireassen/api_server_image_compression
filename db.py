import os
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры подключения
POSTGRES_DB = os.getenv("POSTGRES_DB")  # Убрана запятая!
POSTGRES_CONFIG = {
    "dbname": POSTGRES_DB,
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT")
}

def check_connection():
    """Проверка возможности подключения к БД"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        conn.close()
        return True
    except psycopg2.Error as e:
        logger.error(f"Ошибка подключения: {e}")
        return False

def create_database():
    """Создание БД если не существует"""
    try:
        # Подключаемся к системной БД для создания новой БД
        temp_config = POSTGRES_CONFIG.copy()
        temp_config["dbname"] = "postgres"

        conn = psycopg2.connect(**temp_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Проверяем существование БД
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (POSTGRES_DB,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(POSTGRES_DB)))
            logger.info(f"База данных '{POSTGRES_DB}' создана")
        else:
            logger.info(f"База данных '{POSTGRES_DB}' уже существует")

    except psycopg2.Error as e:
        logger.error(f"Ошибка создания БД: {e}")
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

def create_table():
    """Создание таблицы если не существует"""
    try:
        if not check_connection():
            raise RuntimeError("Нет подключения к БД")

        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        # Проверка существования таблицы
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public' AND tablename = 'files'
            );
        """)
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute("""
                CREATE TABLE files (
                    id UUID PRIMARY KEY,
                    original_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    status VARCHAR(20) DEFAULT 'uploaded',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE OR REPLACE FUNCTION update_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER update_files_timestamp
                BEFORE UPDATE ON files
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
            """)
            conn.commit()
            logger.info("Таблица 'files' создана")
        else:
            logger.info("Таблица 'files' уже существует")

    except psycopg2.Error as e:
        logger.error(f"Ошибка создания таблицы: {e}")
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_database()
    create_table()

