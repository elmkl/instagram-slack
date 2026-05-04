import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

def get_engine():
    return create_engine(os.environ["DATABASE_URL"], poolclass=NullPool)

def ensure_table():
    with get_engine().connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS channel_settings (
                channel TEXT PRIMARY KEY,
                reels BOOLEAN NOT NULL DEFAULT FALSE,
                posts BOOLEAN NOT NULL DEFAULT FALSE,
                stories BOOLEAN NOT NULL DEFAULT FALSE,
                scroll BOOLEAN NOT NULL DEFAULT FALSE
            )
        """))
        conn.commit()

try:
    ensure_table()
except Exception as e:
    print(f"settings table init failed: {e}")

def get_channel_settings(channel):
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text("SELECT reels, posts, stories, scroll FROM channel_settings WHERE channel = :c"), {"c": channel}).fetchone()
            if row:
                return {"reels": row[0], "posts": row[1], "stories": row[2], "scroll": row[3]}
    except Exception as e:
        print(f"get_channel_settings failed: {e}")
    return {"reels": False, "posts": False, "stories": False, "scroll": False}

def toggle_feature(channel, feature):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("""
                INSERT INTO channel_settings (channel, reels, posts, stories, scroll)
                VALUES (:c, FALSE, FALSE, FALSE, FALSE)
                ON CONFLICT (channel) DO NOTHING
            """), {"c": channel})
            conn.execute(text(f"""
                UPDATE channel_settings SET {feature} = NOT {feature} WHERE channel = :c
            """), {"c": channel})
            conn.commit()
            row = conn.execute(text(f"SELECT {feature} FROM channel_settings WHERE channel = :c"), {"c": channel}).fetchone()
            return row[0] if row else False
    except Exception as e:
        print(f"toggle_feature failed: {e}")
        return False

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
            client.chat_postMessage(
                channel=user,
                text="I am not in that channel yet. Please invite me first with `/invite @igscroller`, then run `/igsettings` again."
            )
        else:
            raise