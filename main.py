import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from instagram import init_ig, ig, download_ig_post, download_ig_reel, download_ig_story, fetch_account_reels
from scroll import doomscrollers, post_next_reel
from utils import delete_message

load_dotenv()
os.makedirs("tmp", exist_ok=True)
os.makedirs("tmp/vids", exist_ok=True)
os.makedirs("tmp/pics", exist_ok=True)

# login to instagram for ig API if given access to
init_ig(os.environ.get("INSTAGRAM_SESSIONID"))
app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])
# TODO: make this work even if it fails

# figure out the file size limit in the first instance
team = app.client.team_info()
plan = team["team"].get("plan", "free")
size_limit_mb = 1000 if plan == "pro" else 5

# ts regex
instagram_reel = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?reel/[^\s<>]+")
instagram_post = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?p/[^\s<>]+")
instagram_story = re.compile(r"https://(?:www\.)?instagram\.com/stories/[^\s<>]+")

#### slack ui elements 
@app.action("scroll_next")
def handle_next_button(ack, body, client):
    ack()
    user = body["actions"][0]["value"]
    channel = body["channel"]["id"]
    delete_message(client, channel, body["message"]["ts"])
    if user in doomscrollers:
        doomscrollers[user]["button_ts"] = None
        post_next_reel(user, client, channel, size_limit_mb)

@app.action("scroll_stop")
def handle_stop_button(ack, body, client):
    ack()
    user = body["actions"][0]["value"]
    channel = body["channel"]["id"]
    delete_message(client, channel, body["message"]["ts"])
    if user in doomscrollers:
        session = doomscrollers[user]
        session["active"] = False
        preloaded = session.get("preloaded_path")
        if preloaded and os.path.exists(preloaded):
            os.remove(preloaded)
        del doomscrollers[user]
    client.chat_postEphemeral(channel=channel, user=user, text="Stopped scrolling.")

### scroll command
@app.message(re.compile(r"^scroll (.+)$"))
def handle_scroll(message, say, client, context):
    print("scrolled ", context["matches"][0])
    user = message["user"]
    channel = message["channel"]

    # if they are alraedy doomscrolling no scrool
    if user in doomscrollers:
        return

    from instagram import ig
    if not ig:
        say("Admin is not logged into instagram")
        return

    username = context["matches"][0].strip()
    client.chat_postEphemeral(channel=channel, user=user, text=f"getting reels from @{username}...")

    try:
        reels = fetch_account_reels(username, limit=5)
    except Exception as e:
        print(f"fetch failed: {e}")
        client.chat_postEphemeral(channel=channel, user=user, text=f"Couldn't fetch reels for @{username}. Account may be private or not exist.")
        return

    if not reels:
        client.chat_postEphemeral(channel=channel, user=user, text=f"No reels found for @{username}.")
        return

    doomscrollers[user] = {
        "reels": reels,
        "index": 0,
        "button_ts": None,
        "reel_ts": None,
        "channel": channel,
        "preloaded_path": None,
        "active": True,
    }

    post_next_reel(user, client, channel, size_limit_mb)

@app.message("ping")
def ping(message, say):
    print(f"message: {message}")
    say("pong")

@app.message(instagram_post)
def handle_post(message, say, client):
    from instagram import ig
    if message.get("subtype"):
        return
    if not ig:
        say("not logged into instagram")
        return
    url = re.search(instagram_post, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]
    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")
    try:
        download_ig_post(url, size_limit_mb, client, channel, user)
    except Exception as e:
        client.chat_postEphemeral(channel=channel, user=user, text="Cannot download post. Its either privated or age-restricted.")

@app.message(instagram_reel)
def handle_reel(message, say, client):
    if message.get("subtype"):
        return
    url = re.search(instagram_reel, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]
    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")
    try:
        success = download_ig_reel(url, size_limit_mb, client, channel, user)
        if not success:
            client.chat_postEphemeral(channel=channel, user=user, text="Download failed, file not found.")
    except Exception as e:
        if "empty media response" in str(e):
            client.chat_postEphemeral(channel=channel, user=user, text="The IG reel is either private or age restricted.")
        else:
            client.chat_postEphemeral(channel=channel, user=user, text="Invalid URL or download failed.")

@app.message(instagram_story)
def handle_story(message, say, client):
    from instagram import ig
    if message.get("subtype"):
        return
    if not ig:
        say("Admin is not logged into instagram")
        return
    url = re.search(instagram_story, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]
    client.chat_postEphemeral(channel=channel, user=user, text="Downloading story...")
    try:
        download_ig_story(url, size_limit_mb, client, channel, user)
    except Exception as e:
        client.chat_postEphemeral(channel=channel, user=user, text="Can't download this story. It's either expired or private.")

@app.event("message")
def msg(body, logger):
    pass

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()