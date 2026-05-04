# instagram-slack
<a href="https://slack.com/oauth/v2/authorize?client_id=11009255698258.11005853298405&scope=reactions:write,app_mentions:read,channels:history,channels:read,chat:write,commands,files:write,groups:history,im:history,reactions:read,team:read&user_scope="><img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcSet="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>

This is a Slack bot which downloads & embeds Instagram reels, posts, and stories straight into your channel.

This is being hosted on the free tier of Railway on a nixpacks instance atm so try not to burden the bot too much (like spamming it or inviting it into massive workspaces or channels).

Upon posting an Instagram link, this bot will download & upload it to your Slack.

You can browse an account's reels using the `/scroll` command, and you MUST set up the bot using `/igsettings` before trying the bot out (every feature is toggled off by default to handle huge workspaces).

If a file is too large for the workspace's file limit, compression will automatically be done using ffmpeg.

## Requirements
Python 3, ffmpeg, install dependencies with:
`pip install -r requirements.txt`

## Setup
(disregard all of the above, this is now on HTTP mode and I will rewrite this soon)
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