import os
import re
import yt_dlp
import time
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
load_dotenv()
os.makedirs("tmp", exist_ok=True)

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])
instagram_reel = re.compile(r"https://(?:www\.)?instagram\.com/reel/[^\s<>]+")

@app.message(instagram_reel)
def handle_reel(message, say, client):
    url = re.search(instagram_reel, message["text"]).group(0)
    ts_timestamp = str(int(time.time())) # pmo
    output_path = f"tmp/reel_{ts_timestamp}.mp4"
    ydl_opts = {"outtmpl": output_path, "quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"url: {url}")
    say(f"url: {url}")

@app.event("message")
def msg(body, logger):
    pass

@app.message("ping")
def ping(message, say):
    print(f"message: {message}")
    say("pong")
    
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()