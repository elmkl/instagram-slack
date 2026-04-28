import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])

@app.command("/ping")
def handle_ping(ack, respond):
    ack()
    respond("pong")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()