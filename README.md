# instagram-slack
This is a Slack bot which downloads & embeds Instagram reels, posts, and stories straight into your channel.

Upon posting an Instagram link, this bot will download & upload it to your Slack.

You can browse an account's reels using the /scroll command, and you must set up the bot using /igsettings before trying the bot out (every feature is toggled off by default to handle huge workspaces).

If a file is too large for the workspace's file limit, compression will automatically be done using ffmpeg.

## Requirements
Python 3, ffmpeg, install dependencies with:
`pip install -r requirements.txt`

## Setup
Create an app on Slack and enable Socket Mode.

On the OAuth & Permissions tab, add these bot scopes: `chat:write`, `chat:write.public`, `channels:read`, `groups:read`, `files:write`, and `im:write`

In Event Subscriptions, subscribe to `message.channels` & `message.groups`

In Slash Commands, create /scroll and /igsettings commands

Configure your .env as follows:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...
INSTAGRAM_SESSIONID=...  # optional but allows enables posts/stories/scroll
```
To get your Instagram session ID (optional), log into Instagram in your browser and get the sessionid cookie using debug tools.

Without an Instagram session ID, only public reel links work (through yt-dlp). If you do provide a session ID, please know that these expire over time