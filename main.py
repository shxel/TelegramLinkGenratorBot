import os
import sqlite3
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', None)  # Optional password

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Initialize SQLite database
def init_db():
    """Initialize the SQLite database with tables for authentication and uploads."""
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS authenticated_users
                 (user_id INTEGER PRIMARY KEY,
                  auth_time REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS uploads
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  file_name TEXT,
                  file_size INTEGER,
                  s3_key TEXT,
                  s3_url TEXT,
                  upload_time REAL,
                  expires_at REAL)''')
    conn.commit()
    conn.close()

# Load authenticated users
def load_authenticated_users():
    """Load authenticated user IDs from the database into memory."""
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM authenticated_users')
    users = {row[0] for row in c.fetchall()}
    conn.close()
    return users

# Authentication check
def is_authenticated(user_id, authenticated_users):
    """Check if a user is authenticated."""
    return user_id in authenticated_users

# Rate limit check
def check_rate_limit(user_id):
    """Check if the user is within the daily upload limit (10 files)."""
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    one_day_ago = time.time() - 24 * 60 * 60
    c.execute('SELECT COUNT(*) FROM uploads WHERE user_id = ? AND upload_time >= ?',
              (user_id, one_day_ago))
    count = c.fetchone()[0]
    conn.close()
    return count < 10

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    user_id = update.effective_user.id
    if AUTH_PASSWORD and not is_authenticated(user_id, authenticated_users):
        await update.message.reply_text("Please authenticate using /auth <password>")
        return
    await update.message.reply_text(
        "Hi! Send me any file (up to 50MB) to upload to cloud storage. "
        "You'll get a temporary link (24h). Use /list, /delete, or /regenerate to manage files."
    )

# Auth command
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /auth command for user authentication."""
    user_id = update.effective_user.id
    if not AUTH_PASSWORD:
        await update.message.reply_text("Authentication is not required.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /auth <password>")
        return
    if context.args[0] == AUTH_PASSWORD:
        if user_id not in authenticated_users:
            authenticated_users.add(user_id)
            conn = sqlite3.connect('file_logs.db')
            c = conn.cursor()
            c.execute('INSERT INTO authenticated_users (user_id, auth_time) VALUES (?, ?)',
                      (user_id, time.time()))
            conn.commit()
            conn.close()
        await update.message.reply_text("Authentication successful! You can now use the bot.")
    else:
        await update.message.reply_text("Incorrect password.")

# File handler
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming files and upload them to S3."""
    message = update.message
    user_id = update.effective_user.id

    if AUTH_PASSWORD and not is_authenticated(user_id, authenticated_users):
        await message.reply_text("Please authenticate using /auth <password> first.")
        return

    if not check_rate_limit(user_id):
        await message.reply_text("You've reached your daily limit (10 files/day).")
        return

    file = (message.document or message.photo[-1] if message.photo
            else message.video or message.audio or message.voice)
    if not file:
        await message.reply_text("Please send a valid file (document, photo, video, audio).")
        return

    file_size = file.file_size if hasattr(file, 'file_size') else 0
    if file_size > 50 * 1024 * 1024:
        await message.reply_text("File too large! Max size is 50MB.")
        return

    try:
        file_name = file.file_name if hasattr(file, 'file_name') else f"file_{int(time.time())}"
        file_obj = await file.get_file()
        file_path = await file_obj.download_to_drive()

        s3_key = f"uploads/{user_id}/{int(time.time())}_{file_name}"
        upload_to_s3(file_path, s3_key)
        download_url = generate_presigned_url(s3_key)

        conn = sqlite3.connect('file_logs.db')
        c = conn.cursor()
        upload_time = time.time()
        expires_at = upload_time + 24 * 60 * 60
        c.execute('''INSERT INTO uploads (user_id, file_name, file_size, s3_key, s3_url,
                    upload_time, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, file_name, file_size, s3_key, download_url, upload_time, expires_at))
        file_id = c.lastrowid
        conn.commit()
        conn.close()

        os.remove(file_path)

        response = (
            f"File uploaded! ID: {file_id}\n"
            f"Name: {file_name}\n"
            f"Size: {file_size / 1024:.2f} KB\n"
            f"Link (expires in 24h):\n{download_url}"
        )
        await message.reply_text(response)

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

# List uploads
async def list_uploads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List the user's recent uploads."""
    user_id = update.effective_user.id
    if AUTH_PASSWORD and not is_authenticated(user_id, authenticated_users):
        await update.message.reply_text("Please authenticate using /auth <password> first.")
        return
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    c.execute('SELECT id, file_name, expires_at FROM uploads WHERE user_id = ? ORDER BY upload_time DESC LIMIT 10',
              (user_id,))
    uploads = c.fetchall()
    conn.close()
    if not uploads:
        await update.message.reply_text("No uploaded files found.")
        return
    message = "Your recent uploads:\n"
    for file_id, file_name, expires_at in uploads:
        expires_at_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))
        message += f"ID: {file_id}, Name: {file_name}, Expires: {expires_at_str}\n"
    await update.message.reply_text(message)

# Delete file
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a specific file from S3 and the database."""
    user_id = update.effective_user.id
    if AUTH_PASSWORD and not is_authenticated(user_id, authenticated_users):
        await update.message.reply_text("Please authenticate using /auth <password> first.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /delete <file_id>")
        return
    try:
        file_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid file ID.")
        return
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    c.execute('SELECT s3_key FROM uploads WHERE id = ? AND user_id = ?', (file_id, user_id))
    result = c.fetchone()
    if not result:
        await update.message.reply_text("File not found or you lack permission.")
        conn.close()
        return
    s3_key = result[0]
    s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
    c.execute('DELETE FROM uploads WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("File deleted successfully.")

# Regenerate link
async def regenerate_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a new download link for an existing file."""
    user_id = update.effective_user.id
    if AUTH_PASSWORD and not is_authenticated(user_id, authenticated_users):
        await update.message.reply_text("Please authenticate using /auth <password> first.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /regenerate <file_id>")
        return
    try:
        file_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid file ID.")
        return
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    c.execute('SELECT s3_key FROM uploads WHERE id = ? AND user_id = ?', (file_id, user_id))
    result = c.fetchone()
    if not result:
        await update.message.reply_text("File not found or you lack permission.")
        conn.close()
        return
    s3_key = result[0]
    new_url = generate_presigned_url(s3_key)
    new_expires_at = time.time() + 24 * 60 * 60
    c.execute('UPDATE uploads SET s3_url = ?, expires_at = ? WHERE id = ?',
              (new_url, new_expires_at, file_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"New link (expires in 24h):\n{new_url}")

# S3 upload
def upload_to_s3(file_path, s3_key):
    """Upload a file to S3."""
    s3_client.upload_file(file_path, AWS_BUCKET_NAME, s3_key)

# Generate presigned URL
def generate_presigned_url(s3_key):
    """Generate a 24-hour presigned URL for an S3 object."""
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': AWS_BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=24 * 60 * 60
    )

# Database cleanup job
def cleanup_db(context: ContextTypes.DEFAULT_TYPE):
    """Remove expired upload entries from the database."""
    current_time = time.time()
    conn = sqlite3.connect('file_logs.db')
    c = conn.cursor()
    c.execute('DELETE FROM uploads WHERE expires_at < ?', (current_time,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    print(f"Cleaned up {deleted} expired entries.")

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unexpected errors."""
    if update and update.message:
        await update.message.reply_text("Something went wrong. Try again later.")
    print(f"Error: {context.error}")

def main():
    """Initialize and run the bot."""
    init_db()
    global authenticated_users
    authenticated_users = load_authenticated_users()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))
    application.add_handler(CommandHandler("list", list_uploads))
    application.add_handler(CommandHandler("delete", delete_file))
    application.add_handler(CommandHandler("regenerate", regenerate_link))
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
        handle_file
    ))
    application.add_error_handler(error)

    application.job_queue.run_repeating(cleanup_db, interval=3600, first=10)

    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()