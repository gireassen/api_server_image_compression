import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, HTTPException
import pika
import uuid
import psycopg2
from psycopg2 import sql
from db import create_database, create_table

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

required_env_vars = [
    "RUN_PORT", "RABBITMQ_HOST", "RABBITMQ_USER", "RABBITMQ_PASSWORD",
    "QUEUE_NAME", "DLQ_NAME", "UPLOAD_DIR", "POSTGRES_DB", "POSTGRES_USER",
    "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT", "MAX_FILE_SIZE"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

RUN_PORT = int(os.getenv("RUN_PORT", "8000"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))

POSTGRES_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT")
}

def save_to_db(file_id: str, original_name: str, file_path: str):
    try:
        with psycopg2.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = sql.SQL("""
                    INSERT INTO files (id, original_name, file_path, status)
                    VALUES (%s, %s, %s, 'uploaded')
                """)
                cursor.execute(query, (file_id, original_name, file_path))
                conn.commit()
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise

@app.post("/upload/")
async def upload_file(file: UploadFile):
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if file.size > MAX_FILE_SIZE * 1024 * 1024: # MAX_FILE_SIZE limit
        raise HTTPException(status_code=400, detail="File too large")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, file_id)
    
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())

        save_to_db(file_id, file.filename, file_path)

        credentials = pika.PlainCredentials(
            os.getenv("RABBITMQ_USER"),
            os.getenv("RABBITMQ_PASSWORD")
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.getenv("RABBITMQ_HOST"),
                credentials=credentials
            )
        )
        
        try:
            channel = connection.channel()
            channel.queue_declare(queue=os.getenv("QUEUE_NAME"), arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": os.getenv("DLQ_NAME")
            })
            channel.queue_declare(queue=os.getenv("DLQ_NAME"))
            channel.basic_publish(
                exchange="",
                routing_key=os.getenv("QUEUE_NAME"),
                body=file_path
            )
        finally:
            connection.close()

        logger.info(f"Uploaded file {file.filename} with ID {file_id}")
        return {"message": "File uploaded and sent for processing", "file_id": file_id}

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    create_database()
    create_table()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=RUN_PORT)
