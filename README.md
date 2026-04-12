# Telegram Bot

This is a powerful Telegram bot built with `aiogram`, designed to be deployed on Render or any other platform supporting Python.

## 🚀 Deployment on Render (Option 2 - Free Tier)

This project is configured to run on Render's **Free Tier** by including a small web server that satisfies Render's port binding requirement.

1. Create a new **Web Service** on Render.
2. Connect your GitHub repository.
3. Render will use the `render.yaml` file to configure the service automatically.
4. Add the following **Environment Variables** in the Render dashboard:
   - `BOT_TOKEN`: Your Telegram Bot Token from @BotFather.
   - `MONGO_URL`: Your MongoDB connection URL.
   - `OWNER_IDS`: Your Telegram User ID (comma-separated if multiple).
   - `PORT`: 10000 (Render's default).

## 🛠️ Local Setup

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` and fill in your details.
4. Run the bot:
   ```bash
   python main.py
   ```

## 📂 Project Structure

- `main.py`: Entry point for the bot and dummy web server.
- `commands/`: Bot command handlers.
- `database/`: Database connection and operations.
- `config.py`: Environment variable configuration.
- `render.yaml`: Blueprint for Render deployment.
- `Procfile`: Heroku/Railway process file.
