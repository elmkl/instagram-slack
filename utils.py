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
    duration = float(result.stdout.strip())
    bitrate = int(target_bits / duration)
    subprocess.run([
        "ffmpeg", "-i", input_path, "-b:v", str(bitrate),
        "-bufsize", str(bitrate), "-maxrate", str(bitrate),
        "-y", output_path
    ], capture_output=True)

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