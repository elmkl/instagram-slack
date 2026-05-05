# instagram-slack
<a href="https://instagram-slack-production.up.railway.app/slack/install"><img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcSet="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>
 
This is a Slack bot which downloads & embeds Instagram reels, posts, and stories straight into your channel.
This is being hosted on Railway atm so try not to burden the bot too much (like spamming it or inviting it into massive workspaces or channels).
 
Upon posting an Instagram link, this bot will download & upload it to your Slack.
You can browse an account's reels using the `/scroll` command (defaults to `@starthackclub` if no username is given), and you MUST set up the bot using `/igsettings` before trying it out (every feature is toggled off by default to handle huge workspaces).
If a file is too large for the workspace's file limit, compression will automatically be done using ffmpeg.
 
## Requirements
Python 3, ffmpeg, PostgreSQL, install dependencies with:
`pip install -r requirements.txt`
 
## Setup
Create an app on Slack (HTTP mode, not Socket Mode).
 
On the **OAuth & Permissions** tab, add these bot scopes: `reactions:write`, `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`, `commands`, `files:write`, `groups:history`, `groups:read`, `im:history`, `reactions:read`, `team:read`
 
In **Event Subscriptions** & **Interactivity**, set the request URL to `https://yourapp.com/slack/events`
 
In **Slash Commands**, create `/scroll` and `/igsettings` pointing to `https://yourapp.com/slack/events`
 
In **OAuth & Permissions**, add `https://yourapp.com/slack/oauth_redirect` as a redirect URL
 
Configure your .env as follows:
```
SLACK_SIGNING_SECRET=...
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
DATABASE_URL=...
INSTAGRAM_SESSIONID=...  # optional, enables posts/stories/scroll
COOKIES_B64=...          # optional, base64-encoded cookies.txt for yt-dlp auth
PORT=3000
```
 
To get your Instagram session ID (optional), log into Instagram in your browser and get the `sessionid` cookie using debug tools. Please know that these expire over time.
 
To get `COOKIES_B64`, export your cookies using yt-dlp and base64 encode the file:
```bash
yt-dlp --cookies-from-browser firefox --cookies cookies.txt "https://www.instagram.com"
# on Windows PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt")) | clip
```
 
Without a session ID or cookies, only public reel links work (through yt-dlp).
