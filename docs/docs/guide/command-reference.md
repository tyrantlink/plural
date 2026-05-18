# Command Reference


## Slash Commands
Text-based commands that show up when a user types `/`

### `/account`
These commands synchronize all data between the two accounts; the accounts are internally treated by /plu/ral as one account, with one exception: group shares are per discord account and will not be inherited by the other account.
- `/account share <username>`
  - Request to share data with user account
- `/account accept <username>`
  - Accept `/account share` from user account. 
    - Requires running `/delete_all_data` if user account data is present

### `/api`
- Create and manage your /plu/ral integrations

### `/autoproxy`
Automatically proxy messages.
- `/autoproxy`
  - Toggle autoproxy
- `/autoproxy enable:<true|false>`
  - Enable or disable autoproxy
- `/autoproxy <member>`
  - Set to a specific member immediately
- `/autoproxy global:<true|false>`
  - Whether to proxy everywhere or just in this server; Default is False
- `/autoproxy expiry<1d2h3m4s|None>`
  - Set expiry time (format: 1d2h3m4s); Default is None (never expires)
#### Autoproxy Modes
- `/autoproxy mode front`
  - Using proxy tags will NOT switch the autoproxied member
- `/autoproxy mode latch` [Default Mode]
  - Using proxy tags WILL switch the autoproxied member
- `/autoproxy mode locked`
  - Autoproxy will not switch even if you use proxy tags
- `/autoproxy mode disabled`
  - ALL proxying (including with tags) will be disabled 

### `/config`
- Configure /plu/ral settings.

### `/delete_all_data`
- Delete all your /plu/ral account data

### `/edit`
- Edit your most recent message

### `/export`
- Export your data

### `/group` - WIP

### `/help`
- Get started with the bot

### `/import`
- Import data from /plu/ral, PluralKit, or Tupperbox

### `/member`
- `/member info <member>`
  - Get information about your members
- `/member list`
  - List all your members
- `/member new <member>`
  - Create a new member
- `/member remove <member>`
  - Remove a member
#### Editing Members
- `/member set avatar <member> <image url|upload>`
  - Set a member's avatar
- `/member set bio <member> <text>`
  - Set a member's bio
- `/member set birthday <member> <text>`
  - Set a member's birthday
- `/member set color <member> <hex>`
  - Set a member's color
- `/member set custom_id <member> <text>`
  - Set a member's custom id field
- `/member set group <member> <group>`
  - Set a member's group
- `/member set name <member> <text>`
  - Set a member's name
- `/member set pronouns <member> <text>` 
  - Set a member's pronouns
#### Member Proxy Tags
- `/member tags add <member> prefix <text>`
  - Proxy tag prefix (e.g. {prefix}text)
- `/member tags add <member> suffix <text>`
  - Proxy tag suffix (e.g. text{suffix})
- `/member tags add <member> regex <boolean>`
  - Whether the proxy tag is matched with regex (default: False)
- `/member tags add <member> case_sensitive <boolean>`
  - Whether the proxy tag is case sensitive (default: False)
- `/member tags add <member> avatar <image url|upload>`
  - Avatar for the proxy tag (8MB max)
- `/member tags clear <member>` 
  - Clear all proxy tags from a member
- `/member tags avatar <member>`
  - Sets a avatar for a proxy of a member
- `/member tags remove <member> <proxy_tag>`
  - Remove a proxy tag from a member

### `/ping`
- Interaction latency
  - Average latency to *receive* the last 100 interactions (interactions are commands, button presses, etc.)
- Proxy latency
  - Average latency from a message being sent, to the proxy message being sent for the last 100 proxied messages
    - note: some messages messages will not be included in this average, for example if they include attachments, cloned emoji, dice rolls, etc.

### `/reproxy`
- Reproxy your latest message. Must be the latest message in the channel

### `/say`
- Send a message as a member without a userproxy

### `/stats`
- Get your /plu/ral stats

### `/switch <member>`
- Shortcut for `/autoproxy <member> global:True`
- Sets user to autoproxy to specified member and sets `/autoproxy Global` to True    

### `/userproxy` - WIP

### `/version`
- Get bot version and list of recent changes


## Message Commands
Message commands are commands accessed by right-clicking a message (or hold on mobile), and clicking the `Apps` option. They cannot be entered as chat commands.

### /plu/ral debug
- This command is used to get the proxy logs for any message.
- If used on a proxied message, it will return the logs for the original message.
- If you are not the original author of the message, or a member of the usergroup that proxied the message, some logs will be removed, such as group channel restrictions, and autoproxy information. This is to keep all potentially sensitive information private.

### /plu/ral edit
- This command is used to edit /plu/ral messages, including both traditional webhook messages, and userproxy messages.
- Running this command will respond with a pop-up, allowing you to make changes to the message.

### /plu/ral proxy info
- This command is used to tie a proxied message to the original sender. Use on any proxied message to get the original sender's information.
- #### proxy info without /plu/ral
  - If you do not use /plu/ral and would like to see the original sender's information, <br>you can add the [/plu/ral info bot](https://discord.com/oauth2/authorize?client_id=1358295664882094090) to your account.
  - This is a minimal bot with just the proxy info command, that can be used anywhere.
  - You do **NOT** need to add this bot to your account if you are using /plu/ral, as it is already included in the bot.
  - This bot cannot be added to servers.
