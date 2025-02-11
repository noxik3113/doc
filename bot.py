import os
import logging
import subprocess
import zipfile
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables
HEROKU_API_KEY = os.getenv("HEROKU_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /apps to list Heroku apps or /setapi to set your Heroku API key.")

# Command: /setapi <api_key>
async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global HEROKU_API_KEY
    HEROKU_API_KEY = context.args[0]
    await update.message.reply_text(f"Heroku API key set to: {HEROKU_API_KEY}")

# Command: /apps
async def list_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not HEROKU_API_KEY:
        await update.message.reply_text("Please set your Heroku API key using /setapi <api_key>.")
        return

    try:
        result = subprocess.run(["heroku", "apps", "--json"], env={"HEROKU_API_KEY": HEROKU_API_KEY}, capture_output=True, text=True)
        await update.message.reply_text(result.stdout)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Command: /container <app_name>
async def container(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not HEROKU_API_KEY:
        await update.message.reply_text("Please set your Heroku API key using /setapi <api_key>.")
        return

    app_name = context.args[0]
    try:
        # Log in to Heroku Container Registry
        subprocess.run(["heroku", "container:login"], env={"HEROKU_API_KEY": HEROKU_API_KEY})

        # Pull the Docker image
        subprocess.run(["docker", "pull", f"registry.heroku.com/{app_name}/worker"])

        # Run the container and copy files
        container_id = subprocess.run(["docker", "create", f"registry.heroku.com/{app_name}/worker:latest"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["docker", "cp", f"{container_id}:/app", "./app"])

        # Zip the files
        with zipfile.ZipFile(f"{app_name}.zip", "w") as zipf:
            for root, dirs, files in os.walk("./app"):
                for file in files:
                    zipf.write(os.path.join(root, file))

        # Send the zip file to the user
        await update.message.reply_document(document=open(f"{app_name}.zip", "rb"))

        # Clean up
        subprocess.run(["docker", "rm", container_id])
        os.remove(f"{app_name}.zip")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Main function
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setapi", set_api))
    application.add_handler(CommandHandler("apps", list_apps))
    application.add_handler(CommandHandler("container", container))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
