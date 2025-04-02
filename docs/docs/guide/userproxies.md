# Userproxies
## What are Userproxies?

Userproxies are proxy members attached to a real Discord Bot, giving them banners, bios, and the ability to be used in DMs, Group DMs, and servers without /plu/ral.

**Note: it is currently not possible to autoproxy with userproxies**, you must use the command every time.
This may change in the future through client modding.

### Userproxy Commands
Userproxies have two commands
- `/proxy`\* - Sends a message as the userproxy
  - \* This command can be given a custom name
- `Reply`\* - Replies to a message as the userproxy
  - This is a message command, to use it you must:
    - Right click on a message (or long press on mobile)
    - Click Apps
    - Click the reply command that matches the userproxy icon
  - \* This command will show member name, depending on config

In order to edit messages with the [/plu/ral edit command](./command-reference.md#plu-ral-edit), you must also [add /plu/ral to your account](https://discord.com/oauth2/authorize?client_id=1291501048493768784)

### Creating a Userproxy
This involves creating a bot, so it can be managed by /plu/ral.

#### Configuring Userproxies
For options beyond the token, bio, banner, and proxy command, see the [Userproxy Config](/guide/config.md#userproxy-config) page.

#### Restrictions
- Member names must be at most 32 characters, with tag, if included

#### If you have more than 25 members
- Due to the way Discord works, you will have to create a bot for each member, if you have more than 25 members, head to the [Discord Developer Portal](https://discord.com/developers/applications), and in the Teams tab, click "New Team", then when creating your applications, set them to that team.
- A team can only have 25 applications, but as far as I'm aware, there's no limit to the number of teams you can have, so create as many teams as needed.

#### Creating the Bot
1. Head to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" in the top right
3. Give your application a name, this should be something close to the member name
4. In the Installation tab, make sure both User Install and Guild Install are checked
5. In the Bot tab, click "Reset Token", enter your 2FA or password, and copy the token

#### Creating the Userproxy
1. Use the `/userproxy new` command, choose a member and set the token to the one you copied from part one
  - use the `proxy_command` argument to set a custom command when proxying, recommended if you have more than one userproxy
2. That command will respond with a link, click it and follow the prompt to add the bot to your account
  - This enables you to send messages using the /proxy (or the command you set), you can use this command anywhere, except for servers where you don't have the `Use External Apps` permission

### Userproxies in Servers
#### Proxying without the userproxy invited to the server
You can proxy in servers even without the userproxy invited to the server, with a few limitations
- You can only proxy in servers where you have the `Use External Apps` permission
- If the server uses automod to block masked links, you probably won't be able to properly reply. see [the automod page](/server-guide/automod.md) for more information


#### Inviting the Userproxy to a server
#### Note for Server Admins
- Discord has a bot limit of 50 bots/server, if your server is any bigger than a friend group server, this is not recommended, and normal proxying will still work.
  - This limit only applies to userproxies *invited to the server*, so there's no need to worry about users using external userproxies.
- Do not give these accounts a bot role, or any role that you wouldn't give to the owner of the account. The account owner has full control of the bot, so if you give the bot a permission, you are trusting the account owner with that permission.
- The bot does not request any permissions; if the bot does request permissions, the account owner has modified the link, do not add the bot.

#### What it does
- /plu/ral must also be in the server for the bot to function
- If the userproxy is in the server, when proxying, the bot account will be used
- This enables real replies, since the bot is actually sending the message, searching for messages from the bot, and people can click on the bot to see bio and banner, if set

#### Adding the Userproxy
- Use the command `/userproxy invite`
- If you have the `Manage Server` permission in the server, simply click the link to add the bot to the server.
- Otherwise, give this link to an admin and have them add the bot. Make sure they have read the warnings above.

## Self-hosting
Ability to self-host userproxies is not yet implemented.
