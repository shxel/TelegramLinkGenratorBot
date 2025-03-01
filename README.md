
# 🤖 Telegram File-Transfer Bot 🔗

**A Telegram bot that lets users upload files to AWS S3 and receive secure, temporary download links.**  
Packed with features like **user authentication**, **rate limiting**, and **automated database cleanup** — perfect for managing file transfers securely and efficiently.  

**GitHub Repo**: [TelegramLinkGenratorBot](https://github.com/shxel/TelegramLinkGenratorBot)  

---

## 📋 Table of Contents  
- [✨ Features](#-features)  
- [🛠️ Technologies Used](#️-technologies-used)  
- [📦 Prerequisites](#-prerequisites)  
- [🚀 Setup Instructions](#-setup-instructions)  
- [⚙️ Environment Variables](#️-environment-variables)  
- [🤖 Running the Bot](#-running-the-bot)  
- [💡 Usage](#-usage)  
- [🌐 Deployment](#-deployment)  
- [🗃️ Database Management](#️-database-management)  
- [🤝 Contribution Guidelines](#-contribution-guidelines)  
- [📜 License](#-license)  

---

## ✨ Features  
- 📤 **File Uploads**: Upload documents, images, videos, and more to AWS S3 directly via Telegram.  
- 🔒 **Secure & Temporary Links**: Download links auto-expire after **24 hours**.  
- 🔑 **User Authentication**: Optional password protection to restrict access.  
- 🚫 **Rate Limiting**: Users capped at **10 uploads/day** to prevent spam.  
- 🧹 **Automated Cleanup**: Expired entries scrubbed hourly from the database.  
- 📂 **File Management**: List, delete, or regenerate links with simple commands.  

---

## 🛠️ Technologies Used  
- **Python 3.8+** 🐍  
- **python-telegram-bot** 📡 (Telegram API interactions)  
- **boto3** ☁️ (AWS S3 uploads & presigned URLs)  
- **SQLite** 💾 (Persistent data storage)  
- **python-dotenv** 🔧 (Environment variable management)  

---

## 📦 Prerequisites  
- ✔️ Python 3.8+ installed  
- ✔️ A [Telegram Bot Token](https://t.me/BotFather)  
- ✔️ AWS account with S3 bucket & IAM credentials  
- ✔️ Git (optional, for cloning)  

---

## 🚀 Setup Instructions  

### ⚙️ Environment Variables  
1. **Clone the Repository**:  
   ```bash
   git clone https://github.com/shxel/TelegramLinkGenratorBot.git
   cd TelegramLinkGenratorBot
   ```

2. **Install Dependencies**:  
   ```bash
   pip install python-telegram-bot boto3 python-dotenv
   ```

3. **Configure `.env` File**:  
   Create a `.env` file with:  
   ```ini
   TELEGRAM_TOKEN=your_telegram_bot_token
   AWS_ACCESS_KEY=your_aws_access_key
   AWS_SECRET_KEY=your_aws_secret_key
   AWS_BUCKET_NAME=your_s3_bucket_name
   AWS_REGION=us-east-1  # or your region
   AUTH_PASSWORD=your_optional_password  # Omit for public access
   ```

---

## 🤖 Running the Bot  
1. **Initialize Database** (auto-created on first run):  
2. **Start the Bot**:  
   ```bash
   python bot.py
   ```

---

## 💡 Usage  

### 🔑 Authentication  
- **Password Set?** Send `/auth <password>` to unlock.  
- **No Password?** Bot is open to all!  

### 📤 Uploading Files  
- **Drag & Drop** any file into the chat.  
- **Limit**: ≤50MB/file, 10 uploads/day/user.  

### 🗂️ Managing Files  
- **List Uploads**: `/list` → Last 10 files with IDs and expiry times.  
- **Delete File**: `/delete <file_id>` → Wipes from S3 + database.  
- **Refresh Link**: `/regenerate <file_id>` → New 24-hour link.  

---

## 🌐 Deployment  
**Deploy to Heroku**:  
1. Create App:  
   ```bash
   heroku create your-app-name
   ```
2. Set Config Vars:  
   ```bash
   heroku config:set $(cat .env | sed '/^$/d; /#/d')
   ```
3. Push Code:  
   ```bash
   git push heroku main
   ```
4. Start Worker:  
   ```bash
   heroku ps:scale worker=1
   ```

⚠️ **Note**: Replace SQLite with PostgreSQL for production!  

---

## 🗃️ Database Management  
- **Auto-Cleanup**: Expired entries removed hourly.  
- **Manual Access**: Use tools like [DB Browser for SQLite](https://sqlitebrowser.org/).  

---

## 🤝 Contribution Guidelines  
1. 🍴 **Fork the Repo**  
2. 🌿 **Create Branch**:  
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. 💾 **Commit Changes**:  
   ```bash
   git commit -m "Add amazing feature"
   ```
4. 🚀 **Push to Branch**:  
   ```bash
   git push origin feature/amazing-feature
   ```
5. 📬 **Open a Pull Request**  

---

## 📜 License  
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.  
