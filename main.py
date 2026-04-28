import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])
instagram_reel = re.compile(r"https://www\.instagram\.com/reel/[^\s]+")

@app.message(instagram_reel)
def handle_reel(message, say, client):
    url = re.search(instagram_reel, message["text"]).group(0)
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