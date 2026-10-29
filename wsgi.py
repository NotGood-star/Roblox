import os
import threading
import subprocess
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Web Service Port Online", 200

def launch_discord_process():
    print("Launching independent Discord process...")
    # Launches the bot file as an independent terminal task
    subprocess.Popen(["python", "bot.py"])

# Fires up the bot background instance completely isolated from the web thread
bot_thread = threading.Thread(target=launch_discord_process, daemon=True)
bot_thread.start()
