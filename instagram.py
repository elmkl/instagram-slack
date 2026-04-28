import os
import time
import yt_dlp
from instagrapi import Client
from utils import compress_video

ig = None

def init_ig(session_id):
    global ig
    if session_id:
        ig = Client()
        ig.login_by_sessionid(session_id)
        ig.request_timeout = 30

def fetch_account_reels(username, limit=5):
    # fetch reels directly through ig api
    user_id = ig.user_id_from_username(username)
    time.sleep(1)
    medias = ig.user_medias(user_id, amount=20)
    reels = [f"https://www.instagram.com/reel/{m.code}/" for m in medias if m.media_type == 2 and m.product_type == "clips"]
    return reels[:limit]

def download_reel_to_file(url, output_path):
    # download reel using ytdlp
    ydl_opts = {
        "outtmpl": output_path,
        "quiet": True,
        "merge_output_format": "mp4",
        "format": "bestvideo+bestaudio/best",
        "cookiesfrombrowser": ("firefox",),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_and_post_reel(url, channel, user, client, ts_timestamp, size_limit_mb, preloaded_path=None):
    output_path = f"tmp/vids/feed_{ts_timestamp}.mp4"
    try:
        if preloaded_path and os.path.exists(preloaded_path):
            # use cache isntead of downloading again
            os.rename(preloaded_path, output_path)
            print("using cached reel")
        else:
            download_reel_to_file(url, output_path)
    except Exception as e:
        print(f"download failed: {e}")
        client.chat_postEphemeral(channel=channel, user=user, text="Couldn't download reel, skipping.")
        return None
    if not os.path.exists(output_path):
        return None
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    try:
        if file_size_mb > size_limit_mb:
            compressed_path = f"tmp/vids/feed_{ts_timestamp}_compressed.mp4"
            compress_video(output_path, compressed_path, size_limit_mb * 0.9)
            os.remove(output_path)
            output_path = compressed_path
        response = client.files_upload_v2(channel=channel, file=output_path, filename="reel.mp4")
        return response
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

def download_ig_post(url, size_limit_mb, client, channel, user):
    # handle all otehr forms of posts
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
        # carousel (mix)
        paths = ig.album_download(media_pk, folder="tmp/pics")
    else:
        client.chat_postEphemeral(channel=channel, user=user, text="Unsupported post type.")
        return

    try:
        for path in paths:
            filepath = str(path)
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > size_limit_mb:
                # TODO: compression for this too???
                client.chat_postEphemeral(channel=channel, user=user, text=f"File is {file_size_mb:.1f}MB, too large to upload.")
                continue
            client.files_upload_v2(channel=channel, file=filepath, filename=os.path.basename(filepath))
    finally:
        for path in paths:
            if os.path.exists(str(path)):
                os.remove(str(path))

def download_ig_story(url, size_limit_mb, client, channel, user):
    story_pk = ig.story_pk_from_url(url)
    path = ig.story_download(story_pk, folder="tmp/vids")
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

def download_ig_reel(url, size_limit_mb, client, channel, user):
    import time
    from utils import compress_video
    ts_timestamp = str(int(time.time()))
    output_path = f"tmp/vids/reel_{ts_timestamp}.mp4"

    # use api (if age restriected etc), otherwise use ytdlp
    if ig:
        media_pk = ig.media_pk_from_url(url)
        path = ig.clip_download(media_pk, folder="tmp/vids")
        os.rename(path, output_path)
    else:
        # downlaoding into a tmp (best quality; merge if needed)
        ydl_opts = {
            "outtmpl": output_path,
            "quiet": True,
            "merge_output_format": "mp4",
            "format": "bestvideo+bestaudio/best",
            "cookiesfrombrowser": ("firefox",),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    if not os.path.exists(output_path):
        return False

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
        return True
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)