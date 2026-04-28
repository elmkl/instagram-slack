import os
import re
import yt_dlp
import time
import subprocess
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()
os.makedirs("tmp", exist_ok=True)
os.makedirs("tmp/vids", exist_ok=True)
os.makedirs("tmp/pics", exist_ok=True)

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])

# fetch once at startup
team = app.client.team_info()
plan = team["team"].get("plan", "free")
size_limit_mb = 1000 if plan == "pro" else 5

instagram_reel = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?reel/[^\s<>]+")
instagram_post = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?p/[^\s<>]+")
s
def compress_video(input_path, output_path, target_mb):
    target_bits = target_mb * 8 * 1024 * 1024
    # get duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    bitrate = int(target_bits / duration)
    subprocess.run([
        "ffmpeg", "-i", input_path, "-b:v", str(bitrate),
        "-bufsize", str(bitrate), "-maxrate", str(bitrate),
        "-y", output_path
    ], capture_output=True)

@app.message(instagram_post)
def handle_post(message, say, client):
    # The problem with this is that this requires an ig account, 
    # so I don't know what to do since I don't want to put user/password in .env
    # that's ghetto asf. so:
    # pmo
    say("pmo")

@app.message(instagram_reel)
def handle_reel(message, say, client):
    url = re.search(instagram_reel, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]
    ts_timestamp = str(int(time.time()))
    output_path = f"tmp/vids/reel_{ts_timestamp}.mp4"

    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")
    # downlaoding into a temp file (best quality; merge if needed)
    yt_dlp_settings = {
        "outtmpl": output_path,
        "quiet": True,
        "merge_output_format": "mp4",
        "format": "bestvideo+bestaudio/best",
        "cookiesfrombrowser": ("firefox",),
    }
    #proceed with downloading
    try:
        with yt_dlp.YoutubeDL(yt_dlp_settings) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        if "empty media response" in str(e):
            client.chat_postEphemeral(channel=channel, user=user, text="This reel is private or age restricted.")
        else:
            client.chat_postEphemeral(channel=channel, user=user, text="Invalid URL or download failed.")
        return

    if not os.path.exists(output_path):
        client.chat_postEphemeral(channel=channel, user=user, text="Download failed, file not found.")
        return

    # check the file size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    try:
        if file_size_mb > size_limit_mb:
            # compress the video
            client.chat_postEphemeral(channel=channel, user=user, text=f"File is {file_size_mb:.1f}MB, we are compressing...")
            compressed_path = f"tmp/vids/reel_{ts_timestamp}_compressed.mp4"
            compress_video(output_path, compressed_path, size_limit_mb * 0.9)
            os.remove(output_path)
            output_path = compressed_path
        client.files_upload_v2(channel=channel, file=output_path, filename="reel.mp4")
        print("video sent")
    finally:
        if os.path.exists(output_path):
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