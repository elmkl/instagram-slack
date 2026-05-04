import os
import subprocess

# TODO: dont be so dependent on ffmpeg i feel it may be vulnerable to malicious imput
# i dunno doe
def compress_video(input_path, output_path, target_mb):
    target_bits = target_mb * 8 * 1024 * 1024
    # get duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True
    )
    if not result.stdout.strip():
        raise ValueError(f"ffprobe failed: {result.stderr}")
    duration = float(result.stdout.strip())
    bitrate = int(target_bits / duration)

    # scale down resolution if target is small — 1080p60 can't fit in 5MB
    scale = "scale=-2:480" if target_mb < 15 else "scale=-2:720"

    result = subprocess.run([
        "ffmpeg", "-i", input_path,
        "-vf", scale,
        "-b:v", str(bitrate),
        "-bufsize", str(bitrate * 2),
        "-maxrate", str(int(bitrate * 1.5)),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "64k",
        "-movflags", "+faststart",
        "-y", output_path
    ], capture_output=True)

    if result.returncode != 0:
        raise ValueError(f"ffmpeg failed: {result.stderr.decode()}")
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        raise ValueError("ffmpeg produced empty output")

def delete_message(client, channel, ts):
    if not ts:
        return
    try:
        result = client.chat_delete(channel=channel, ts=ts)
        print(f"deleted message {ts}: {result['ok']}")
    except Exception as e:
        print(f"couldn't delete message {ts}: {e}")

def get_message_ts(response, channel):
    # ts of message ts ts ts 
    shares = response.get("file", {}).get("shares", {})
    channel_shares = shares.get("public", shares.get("private", {}))
    entries = channel_shares.get(channel)
    if entries:
        return entries[0]["ts"]
    return None