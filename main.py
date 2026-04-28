import os
import re
import yt_dlp
import time
import subprocess
from instagrapi import Client
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()
os.makedirs("tmp", exist_ok=True)
os.makedirs("tmp/vids", exist_ok=True)
os.makedirs("tmp/pics", exist_ok=True)

# login to instagram if session id is provided
ig = None
if os.environ.get("INSTAGRAM_SESSIONID"):
    ig = Client()
    ig.login_by_sessionid(os.environ["INSTAGRAM_SESSIONID"])

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])

# figure out the file size limit in one go
team = app.client.team_info()
plan = team["team"].get("plan", "free")
size_limit_mb = 1000 if plan == "pro" else 5

# fuck these regexes
instagram_reel = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?reel/[^\s<>]+")
instagram_post = re.compile(r"https://(?:www\.)?instagram\.com/(?:[^/]+/)?p/[^\s<>]+")
instagram_story = re.compile(r"https://(?:www\.)?instagram\.com/stories/[^\s<>]+")

# cringe
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
    if not ig:
        say("not logged into instagram")
        return
    
    url = re.search(instagram_post, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]
    ts_timestamp = str(int(time.time()))

    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")

    try:
        media_pk = ig.media_pk_from_url(url)
        media = ig.media_info(media_pk)

        if media.media_type == 1:
            # photo
            path = ig.photo_download(media_pk, folder="tmp/pics")
            paths = [path]
        elif media.media_type == 2:
            # video post
            path = ig.clip_download(media_pk, folder="tmp/vids")
            paths = [path]
        elif media.media_type == 8:
            # carousel (mixed photos/videos)
            paths = ig.album_download(media_pk, folder="tmp/pics")
        else:
            client.chat_postEphemeral(channel=channel, user=user, text="Unsupported post type.")
            return
    except Exception as e:
        client.chat_postEphemeral(channel=channel, user=user, text="Couldn't download this post. It may be private or age-restricted.")
        return

    try:
        for path in paths:
            filepath = str(path)
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > size_limit_mb:
                # TODO: compressioon for this too???
                client.chat_postEphemeral(channel=channel, user=user, text=f"File is {file_size_mb:.1f}MB, too large to upload.")
                continue
            client.files_upload_v2(channel=channel, file=filepath, filename=os.path.basename(filepath))
    finally:
        for path in paths:
            if os.path.exists(str(path)):
                os.remove(str(path))

@app.message(instagram_reel)
def handle_reel(message, say, client):
    url = re.search(instagram_reel, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]
    ts_timestamp = str(int(time.time()))
    output_path = f"tmp/vids/reel_{ts_timestamp}.mp4"

    client.chat_postEphemeral(channel=channel, user=user, text="Downloading...")

    # use instagrapi if available, else fall back to yt-dlp
    try:
        if ig:
            media_pk = ig.media_pk_from_url(url)
            path = ig.clip_download(media_pk, folder="tmp/vids")
            os.rename(path, output_path)
        else:
            # downlaoding into a temp file (best quality; merge if needed)
            yt_dlp_settings = {
                "outtmpl": output_path,
                "quiet": True,
                "merge_output_format": "mp4",
                "format": "bestvideo+bestaudio/best",
                "cookiesfrombrowser": ("firefox",),
            }
            with yt_dlp.YoutubeDL(yt_dlp_settings) as ydl:
                ydl.download([url])
    except Exception as e:
        if "empty media response" in str(e):
            client.chat_postEphemeral(channel=channel, user=user, text="This reel is either private or age restricted.")
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
            client.chat_postEphemeral(channel=channel, user=user, text=f"File is {file_size_mb:.1f}MB, compressing...")
            compressed_path = f"tmp/vids/reel_{ts_timestamp}_compressed.mp4"
            compress_video(output_path, compressed_path, size_limit_mb * 0.9)
            os.remove(output_path)
            output_path = compressed_path
        client.files_upload_v2(channel=channel, file=output_path, filename="reel.mp4")
        print("video sent")
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

@app.message(instagram_story)
def handle_story(message, say, client):
    if not ig:
        say("not logged into instagram")
        return
    
    url = re.search(instagram_story, message["text"]).group(0)
    channel = message["channel"]
    user = message["user"]

    client.chat_postEphemeral(channel=channel, user=user, text="Downloading story...")

    try:
        story_pk = ig.story_pk_from_url(url)
        path = ig.story_download(story_pk, folder="tmp/vids")
    except Exception as e:
        client.chat_postEphemeral(channel=channel, user=user, text="Couldn't download this story. It's either expired or private.")
        return

    filepath = str(path)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    try:
        if file_size_mb > size_limit_mb:
            # TODO: compress this too
            client.chat_postEphemeral(channel=channel, user=user, text=f"File is {file_size_mb:.1f}MB, too large to upload.")
            return
        client.files_upload_v2(channel=channel, file=filepath, filename=os.path.basename(filepath))
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

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