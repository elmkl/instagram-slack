import os
import threading
import requests
from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def index():
    return open("index.html").read()

@app.route("/slack/oauth_redirect")
def oauth_redirect():
    code = request.args.get("code")
    if not code:
        return "Missing code.", 400

    response = requests.post("https://slack.com/api/oauth.v2.access", data={
        "code": code,
        "client_id": os.environ["SLACK_CLIENT_ID"],
        "client_secret": os.environ["SLACK_CLIENT_SECRET"],
    })

    data = response.json()
    if not data.get("ok"):
        return f"OAuth failed: {data.get('error')}", 400

    return """
<h1>Thank you for installing! Head back to Slack and follow the instructions</h1>
<h2>Instructions:</h2>

<p>By default, nothing is enabled. A channel owner must enable features first.</p>

<h3>Setup (channel owners)</h3>
<ol>
  <li>Install the bot into a workspace (preferably one you own, you are here!)</li>
  <li>Invite the bot to a channel: <code>/invite @igscroller</code></li>
  <li>Run <code>/igsettings</code> to open the settings panel</li>
  <li>Toggle on whichever features you want: Reels, Posts, Stories, Scroll</li>
</ol>

<h3>Features</h3>
<ul>
  <li><strong>Reels / Posts / Stories</strong>: paste any Instagram link in the channel and the bot will download and upload it directly to Slack</li>
  <li><strong>/igscroll &lt;username&gt;</strong>: browse an account's reels one by one with next/stop buttons</li>
</ul>

<h3>Notes</h3>
<ul>
  <li>Only the channel creator can change settings</li>
  <li>Settings are saved per channel</li>
  <li>Private or age-restricted content may not be downloadable</li>
</ul>
    """

def run():
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

def start():
    threading.Thread(target=run, daemon=True).start()