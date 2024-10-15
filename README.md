# /plu/ral
**Add /plu/ral to your server: https://plural.gg/invite**

/plu/ral is a plural/roleplay proxy Discord bot built to modern discord app standards, using slash commands and interactions, including autocomplete for member and group names, and an interactive message command for editing, so no more copying your entire message to edit.

Made to be a simpler alternative to PluralKit and Tupperbox, no profiles, no public information, just groups, members, and proxies, and with the implementation of the new Discord features, there's no need for a web dashboard, everything can easily be done in Discord. if you're coming from PluralKit or Tupperbox, you can import your existing data with a single command.

Once you've added the bot, you can just type `/` in any text channel to see a list of commands and their descriptions, or run `/help` to see instructions on getting started.

If you need any additional information, or have any questions, you can join my support server here: https://discord.gg/4mteVXBDW7

## Features
- Import your existing data from PluralKit or Tupperbox with `/import`
- No system, just groups and members
- Make new groups with `/group new`
- Add members to groups with `/member new`
- Add a proxy for a member with `/member proxy add`
- Toggle autoproxy with `/autoproxy`
- Edit messages by right-clicking (hold on mobile) a message, clicking "Apps", then "/plu/ral edit"
- Delete messages by reacting with ❌
- And a fully featured API, anything you can do with the bot, you can do with the API https://api.plural.gg/docs

### Planned Features
- A GUI management menu for groups and members, accessible with `/manage`
- Avatar uploading via API
- Sharing groups between discord accounts (already built into the backend, if you urgently need this just join the support server and DM me (@tyrantlink))

# Hosting it yourself
If you don't plan on hosting it yourself, you can simply add the bot with https://plural.gg/invite and stop reading here.

Running the bot only requires MongoDB, a domain, a reverse proxy and either Docker (recommended) or Python

## Prerequisites
- MongoDB - Setting up a MongoDB instance is out of the scope of this guide, but you can find instructions on how to do so here: https://docs.mongodb.com/manual/installation

- Docker or Python
    - Docker - If you're using Docker, you can find instructions on how to install it here: https://docs.docker.com/get-docker/
    - Python - If you're not using Docker, you'll need Python 3.12 or higher, you can find instructions on how to install it here: https://www.python.org/downloads/

- A Discord Bot
    1. Navigate to the Discord Developer Portal: https://discord.com/developers/applications
    2. Click "New Application" in the top right corner and give your bot a name, then click "Create"
    3. Click on the "Bot" tab on the left side of the screen, and scroll down to the "Privileged Gateway Intents" section, and enable the "Message Content" intent for the bot to function properly
    4. Click "Reset Token" and enter either your password or 2FA code, then save the token somewhere safe, you'll need it later
    5. Click on the "Installation" tab on the left side of the screen, uncheck the "User Install" box
    6. Scroll down to the "Default Install Settings" section, and add the "bot" scope to the "Guild Install" section
    7. In the Permissions section, add the following permissions:
        - `Attach Files`
        - `Embed Links`
        - `Manage Messages`
        - `Manage Webhooks`
        - `Send Messages`
        - `Send Messages in Threads`
        - `Use External Emojis`
        - `View Channels`

- A Domain and Reverse Proxy
    - You'll need a domain to host the bot's API on, required for avatar URLs, and a reverse proxy to forward requests to the bot's API, I recommend using Caddy, you can find instructions on how to install it here: https://caddyserver.com/docs/install
    - **Note:** you will need to set up 

## Setup

1. Clone this repository and enter the directory with `git clone https://github.com/tyrantlink/plural && cd plural`
2. Copy `project.toml.example` to `project.toml` and fill the following fields:
    - `bot_token`: Your bot token you copied earlier
    - `mongo_uri`: Your MongoDB URI
    - `base_url`: The base URL for the bot's API, used for avatar URLs
    - `import_proxy_channel_id`: set to the channel ID of a private channel that ideally only has the bot,
    due to pluralkit storing images on discord's cdn, and discord expiring these urls, the bot needs to send them into a channel to refresh the urls before importing them, they are immediately deleted after being sent.
3. (I will make a docker-compose file for this later so i'm not going to write this out yet)


