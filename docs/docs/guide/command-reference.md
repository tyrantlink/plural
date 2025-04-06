# Command Reference

This page is NOT a comprehensive list of all commands available in /plu/ral.

This page is for extra information about commands that may not be clear from their descriptions.

For a complete list of commands, simply type `/` in a discord channel with /plu/ral in it, and select /plu/ral's icon on the left.

## Message Commands
Message commands are commands accessed by right-clicking a message (or hold on mobile), and clicking the `Apps` option.

### /plu/ral debug
This command is used to get the proxy logs for any message.
If used on a proxied message, it will return the logs for the original message.

If you are not the original author of the message, or a member of the usergroup that proxied the message, some logs will be removed, such as group channel restrictions, and autoproxy information. This is to keep all potentially sensitive information private.

### /plu/ral edit
This command is used to edit /plu/ral messages, including both traditional webhook messages, and userproxy messages.

Running this command will respond with a pop-up, allowing you to make changes to the message.

### /plu/ral proxy info
This command is used to tie a proxied message to the original sender. Use on any proxied message to get the original sender's information.

#### proxy info without /plu/ral
If you do not use /plu/ral and would like to see the original sender's information, <br>
you can add the [/plu/ral info bot](https://discord.com/oauth2/authorize?client_id=1358295664882094090) to your account.

This is a minimal bot with just the proxy info command, that can be used anywhere.

You do **NOT** need to add this bot to your account if you are using /plu/ral, as it is already included in the bot.

This bot cannot be added to servers.

## General
### /ping
- Interaction latency
  - Average latency to *receive* the last 100 interactions (interactions are commands, button presses, etc.)
- Proxy latency
  - Average latency from a message being sent, to the proxy message being sent for the last 100 proxied messages
    - note: some messages messages will not be included in this average, for example if they include attachments, cloned emoji, dice rolls, etc.

### /switch
This command is nothing more than a shortcut to `/autoproxy`, with the global option set to `True`.