import os
import re
from flask import Flask, request, redirect
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore
from instagram import init_ig, ig, download_ig_post, download_ig_reel, download_ig_story, fetch_account_reels
from scroll import doomscrollers, post_next_reel
from utils import delete_message
from settings import get_channel_settings, toggle_feature, is_channel_owner, post_settings_message

load_dotenv()
os.makedirs("tmp", exist_ok=True)
os.makedirs("tmp/vids", exist_ok=True)
os.makedirs("tmp/pics", exist_ok=True)
os.makedirs("./data/installations", exist_ok=True)
os.makedirs("./data/states", exist_ok=True)

# login to instagram for ig API if given access to
init_ig(os.environ.get("INSTAGRAM_SESSIONID"))

app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    oauth_settings=OAuthSettings(
        client_id=os.environ["SLACK_CLIENT_ID"],
        client_secret=os.environ["SLACK_CLIENT_SECRET"],
        scopes=["reactions:write", "app_mentions:read", "channels:history", "channels:read",
                "chat:write", "commands", "files:write", "groups:history", "groups:read",
                "im:history", "reactions:read", "team:read"],
        installation_store=FileInstallationStore(base_dir="./data/installations"),
        state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="./data/states"),
    )
)

# ts regex
instagram_reel = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?reel/[^\s<>]+")
instagram_post = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?p/[^\s<>]+")
instagram_story = re.compile(r"https://(?:www\.)?instagram\.com/stories/[^\s<>]+")

def get_size_limit(client):
    try:
        team = client.team_info()
        plan = team["team"].get("plan", "free")
        return 1000 if plan == "pro" else 5
    except:
        return 5

@app.error
def handle_errors(error, body, logger):
    if "missing_scope" in str(error):
        try:
            channel = body.get("event", {}).get("channel") or body.get("channel_id")
            user = body.get("event", {}).get("user") or body.get("user_id")
            if channel and user:
                app.client.chat_postEphemeral(
                    channel=channel,
                    user=user,
                    text="This workspace needs to reinstall the bot with updated permissions. <https://instagram-slack-production.up.railway.app/slack/install|Click here to reinstall.>"
                )
        except:
            pass
    logger.exception(error)

#### slack ui elements
@app.action("scroll_next")
def handle_next_button(ack, body, client):
    ack()
    user = body["actions"][0]["value"]
    channel = body["channel"]["id"]
    delete_message(client, channel, body["message"]["ts"])
    if user in doomscrollers:
        doomscrollers[user]["button_ts"] = None
        post_next_reel(user, client, channel, get_size_limit(client))

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

### settings slash command
@app.command("/igsettings")
def handle_settings(ack, command, client):
    ack()
    user = command["user_id"]
    channel = command["channel_id"]
    if not is_channel_owner(client, channel, user):
        client.chat_postEphemeral(channel=channel, user=user, text="Only the channel owner can change settings.")
        return
    post_settings_message(client, channel, user)

### settings toggle actions
def make_toggle_handler(feature):
    def handler(ack, body, client):
        ack()
        user = body["user"]["id"]
        channel = body["actions"][0]["value"]
        if not is_channel_owner(client, channel, user):
            client.chat_postEphemeral(channel=channel, user=user, text="Only the channel owner can change settings.")
            return
        toggle_feature(channel, feature)
        post_settings_message(client, channel, user)
    return handler

app.action("setting_reels")(make_toggle_handler("reels"))
app.action("setting_posts")(make_toggle_handler("posts"))
app.action("setting_stories")(make_toggle_handler("stories"))
app.action("setting_scroll")(make_toggle_handler("scroll"))

### scroll slash command
@app.command("/igscroll")
def handle_scroll(ack, command, client):
    ack()
    user = command["user_id"]
    channel = command["channel_id"]

    if not get_channel_settings(channel).get("scroll"):
        client.chat_postEphemeral(channel=channel, user=user, text="Scroll is not enabled in this channel.")
        return

    # if they are alraedy doomscrolling no scrool
    if user in doomscrollers:
        return

    from instagram import ig
    if not ig:
        client.chat_postEphemeral(channel=channel, user=user, text="Admin is not logged into instagram.")
        return

    username = command["text"].strip()
    if not username:
        client.chat_postEphemeral(channel=channel, user=user, text="Usage: /igscroll <username>")
        return

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

    post_next_reel(user, client, channel, get_size_limit(client))

@app.message("ping")
def ping(message, say):
    print(f"message: {message}")
    say("pong")

@app.message(instagram_post)
def handle_post(message, say, client):
    if message.get("subtype"):
        return
    channel = message["channel"]
    user = message["user"]
    if not get_channel_settings(channel).get("posts"):
        return
    from instagram import ig
    if not ig:
        say("not logged into instagram")
        return
    url = re.search(instagram_post, message["text"]).group(0)
    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")
    try:
        download_ig_post(url, get_size_limit(client), client, channel, user)
    except Exception as e:
        client.chat_postEphemeral(channel=channel, user=user, text="Cannot download post. Its either privated or age-restricted.")

@app.message(instagram_reel)
def handle_reel(message, say, client):
    if message.get("subtype"):
        return
    channel = message["channel"]
    user = message["user"]
    if not get_channel_settings(channel).get("reels"):
        return
    url = re.search(instagram_reel, message["text"]).group(0)
    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")
    try:
        success = download_ig_reel(url, get_size_limit(client), client, channel, user)
        if not success:
            client.chat_postEphemeral(channel=channel, user=user, text="Download failed, file not found.")
    except Exception as e:
        if "empty media response" in str(e):
            client.chat_postEphemeral(channel=channel, user=user, text="The IG reel is either private or age restricted.")
        else:
            client.chat_postEphemeral(channel=channel, user=user, text="Invalid URL or download failed.")

@app.message(instagram_story)
def handle_story(message, say, client):
    if message.get("subtype"):
        return
    channel = message["channel"]
    user = message["user"]
    if not get_channel_settings(channel).get("stories"):
        return
    from instagram import ig
    if not ig:
        say("Admin is not logged into instagram")
        return
    url = re.search(instagram_story, message["text"]).group(0)
    client.chat_postEphemeral(channel=channel, user=user, text="Downloading story...")
    try:
        download_ig_story(url, get_size_limit(client), client, channel, user)
    except Exception as e:
        client.chat_postEphemeral(channel=channel, user=user, text="Can't download this story. It's either expired or private.")

@app.event("message")
def msg(body, logger):
    pass

### flask
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/")
def index():
    try:
        return open("index.html").read()
    except:
        return "ig doomscroller bot"

@flask_app.route("/slack/events", methods=["POST"])
def events():
    return handler.handle(request)

@flask_app.route("/slack/oauth_redirect")
def oauth_redirect():
    # let bolt handle the oauth exchange, then redirect to index with team+app params
    code = request.args.get("code")
    if code:
        import requests as req
        resp = req.post("https://slack.com/api/oauth.v2.access", data={
            "code": code,
            "client_id": os.environ["SLACK_CLIENT_ID"],
            "client_secret": os.environ["SLACK_CLIENT_SECRET"],
        }).json()
        if resp.get("ok"):
            team_id = resp.get("team", {}).get("id", "")
            app_id = resp.get("app_id", "")
            return redirect(f"/?team={team_id}&app={app_id}")
    return handler.handle(request)

@flask_app.route("/slack/install")
def install():
    return handler.handle(request)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)