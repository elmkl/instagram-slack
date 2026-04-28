import os
import time
import threading
from utils import delete_message, get_message_ts
from instagram import download_reel_to_file, download_and_post_reel

# store active scroll sessions per user
doomscrollers = {}

def preload_next_reel(session, size_limit_mb):
    # download next reel in background while user watches current one
    reels = session["reels"]
    next_index = session["index"]
    if next_index >= len(reels):
        return
    next_url = reels[next_index]
    next_path = f"tmp/vids/preload_{next_index}_{int(time.time())}.mp4"
    try:
        download_reel_to_file(next_url, next_path)
        if session.get("active"):
            session["preloaded_path"] = next_path
            print(f"preloaded reel {next_index}")
        else:
            os.remove(next_path)
    except Exception as e:
        print(f"preload failed: {e}")
        session["preloaded_path"] = None

def post_buttons(client, channel, user, remaining):
    button_text = f"Next ({remaining} left)" if remaining > 0 else "No more reels"
    response = client.chat_postMessage(
        channel=channel,
        text="Next reel",
        blocks=[
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": button_text},
                        "action_id": "scroll_next",
                        "value": user,
                        **({"style": "primary"} if remaining > 0 else {})
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Stop"},
                        "action_id": "scroll_stop",
                        "value": user,
                        "style": "danger"
                    }
                ]
            }
        ]
    )
    return response["ts"]

def post_next_reel(user, client, channel, size_limit_mb):
    session = doomscrollers.get(user)
    if not session:
        return
    reels = session["reels"]
    index = session["index"]

    if index >= len(reels):
        client.chat_postEphemeral(channel=channel, user=user, text="No more reels in queue.")
        del doomscrollers[user]
        return

    # delete previous reel and button messages
    delete_message(client, channel, session["button_ts"])
    delete_message(client, channel, session["reel_ts"]) # TODO: verify if this works
    session["button_ts"] = None
    session["reel_ts"] = None

    # let user know we are loading the next one
    client.chat_postEphemeral(channel=channel, user=user, text=f"Loading reel {index + 1} of {len(reels)}...")

    ts_timestamp = str(int(time.time()))

    # use cache if it is available
    preloaded_path = session.pop("preloaded_path", None)
    response = download_and_post_reel(reels[index], channel, user, client, ts_timestamp, size_limit_mb, preloaded_path)

    if response:
        session["index"] += 1
        remaining = len(reels) - session["index"]

        # store reel message ts for deletion on next scroll
        session["reel_ts"] = get_message_ts(response, channel)

        # preload next reel in background
        threading.Thread(target=preload_next_reel, args=(session, size_limit_mb), daemon=True).start()

        # post buttons after the video
        session["button_ts"] = post_buttons(client, channel, user, remaining)
        print(f"posted buttons with ts: {session['button_ts']}")