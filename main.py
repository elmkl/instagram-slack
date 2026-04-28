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
instagram_post = re.compile(r"https://(?:www\.)?instagram\.com/p/[^\s<>]+")

@app.message(instagram_post)
def handle_post(message, say, client):
    url = re.search(instagram_post, message["text"]).group(0)
    say(f"no")

@app.message(instagram_reel)
def handle_reel(message, say, client):
    #before everything, figure out the file limit
    team = client.team_info()
    plan = team["team"].get("plan", "free")
    size_limit_mb = 1000 if plan == "pro" else 5

    # downlaoding into a temp file (best quality; merge if needed)
    url = re.search(instagram_reel, message["text"]).group(0)
    channel = message["channel"]
    ts_timestamp = str(int(time.time())) # pmo
    output_path = f"tmp/reel_{ts_timestamp}.mp4"
    yt_dlp_settings = {
        "outtmpl": output_path,
        "quiet": True,
        "merge_output_format": "mp4",
        "format": "bestvideo+bestaudio/best",
        "cookiesfrombrowser": ("firefox",),
    }
    try:
        with yt_dlp.YoutubeDL(yt_dlp_settings) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        if "empty media response" in str(e):
            say("this reel is private or age restricted")
        else:
            say("invalid url")
        return
    print(f"url: {url}")
    print(f"vidya path: {output_path}")

    # check the file size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    if file_size_mb > size_limit_mb:
        say(f"fuck")
        print(f"compress please")
        return
    
    # upload the video
    try:
        client.files_upload_v2(channel=channel, file=output_path, filename="reel.mp4")
    finally:
        os.remove(output_path)

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