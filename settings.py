import json
import os

SETTINGS_FILE = "settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def get_channel_settings(channel):
    settings = load_settings()
    return settings.get(channel, {
        "reels": False,
        "posts": False,
        "stories": False,
        "scroll": False,
    })

def toggle_feature(channel, feature):
    settings = load_settings()
    if channel not in settings:
        settings[channel] = {"reels": False, "posts": False, "stories": False, "scroll": False}
    settings[channel][feature] = not settings[channel].get(feature, False)
    save_settings(settings)
    return settings[channel][feature]

def is_channel_owner(client, channel, user):
    try:
        info = client.conversations_info(channel=channel)
        return info["channel"].get("creator") == user
    except Exception as e:
        print(f"couldn't check channel owner: {e}")
        return False

def post_settings_message(client, channel, user):
    s = get_channel_settings(channel)

    def status(val):
        return "✅" if val else "❌"

    try:
        client.chat_postEphemeral(
            channel=channel,
            user=user,
            text="Channel settings",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "channel settings, click to toggle features on and off"}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": f"{status(s['reels'])} Reels"},
                            "action_id": "setting_reels",
                            "value": channel,
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": f"{status(s['posts'])} Posts"},
                            "action_id": "setting_posts",
                            "value": channel,
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": f"{status(s['stories'])} Stories"},
                            "action_id": "setting_stories",
                            "value": channel,
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": f"{status(s['scroll'])} Scroll"},
                            "action_id": "setting_scroll",
                            "value": channel,
                        },
                    ]
                }
            ]
        )
    except Exception as e:
        if "not_in_channel" in str(e):
            # bot isn't in the channel yet, DM the user instead
            client.chat_postMessage(
                channel=user,
                text="I'm not in that channel yet. Please invite me first with `/invite @igscroller`, then run `/igsettings` again."
            )
        else:
            raise