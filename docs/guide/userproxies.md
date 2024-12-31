# Userproxies
## What are Userproxies?

Userproxies are proxy members attached to a real Discord Bot, giving them banners, bios, and the ability to be used in DMs, Group DMs, and servers without /plu/ral.

### Creating a Userproxy

This involves creating a bot, and giving the token token to /plu/ral so it can be managed by /plu/ral

#### Restrictions
- Member names must be at most 32 characters, with group tag, if included

#### If you have more than 25 members
- Due to the way Discord works, you will have to create a bot for each member, if you have more than 25 members, head to the [Discord Developer Portal](<https://discord.com/developers/applications>), and in the Teams tab, click "New Team", then when creating your applications, set them to that team.
- A team can only have 25 applications, but as far as I'm aware, there's no limit to the number of teams you can have, so create as many teams as needed.

#### Creating the Bot
- Head to the [Discord Developer Portal](<https://discord.com/developers/applications>)
- Click "New Application" in the top right
- Give your application a name, this should be something close to the member name
- In the Installation tab, make sure both User Install and Guild Install are checked
- In the Bot tab, click "Reset Token", enter your 2FA or password, and copy the token

#### Creating the Userproxy
- Use the `/member userproxy new` command, choose a member and set the token to the one you copied from part one
  - use the `proxy_command` argument to set a custom command when proxying, recommended if you have more than one userproxy
  - by default, the bot token is stored, this enables automatic syncing and the usage of guild userproxies, you can disable this if you choose, but you will have to sync member changes manually by supplying the bot token to `/member userproxy sync`
  - by default, the group tag is not included in the userproxy name, if you wish to include it, set `include_group_tag` to `True`
- That command should respond with a link, click that link to add the bot to your account
- This enables you to send messages using the /proxy (or the command you set), you can use this command anywhere, except for servers where you don't have the `Use External Apps` permission
- To edit messages, you must also [add /plu/ral to your account](https://discord.com/oauth2/authorize?client_id=1291501048493768784), this also allows you to manage your members from anywhere.


### Userproxies in Servers
#### Proxying without the userproxy invited to the server
You can proxy in servers even without the userproxy invited to the server, with a few limitations
- You can only proxy in servers where you have the `Use External Apps` permission
- If the server uses automod to block masked links, you probably won't be able to properly reply. see [the automod page](./server-guide/automod.md) for more information


#### Inviting the Userproxy to a server
#### Note for Server Admins
- Discord has a bot limit of 50 bots/server, if your server is any bigger than a friend group server, this is not recommended, and normal proxying will still work.
- Do not give these accounts a bot role, or any role that you wouldn't give to the owner of the account, The account owner has full control of the bot, so if you give the bot a permission, you are trusting the account owner with that permission.
- The bot does not request any permissions, if the bot does request permissions, the account owner has modified the link, do not add the bot.

#### What it does
- /plu/ral must also be in the server for the bot to function
- If the userproxy is in the server, when proxying, the bot account will be used
- This enables real replies, since the bot is actually sending the message, searching for messages from the bot works, and people can click on the bot to see bio and banner, if set

#### Adding the Userproxy
- Use the command `/member userproxy invite`
- If you have the `Manage Server` permission in the server you want to add the bot to, simply click the link to add the bot to the server
- Otherwise, give this link to an admin and have them add the bot, make sure they have read the warnings above.


## Self-hosting
See the [self-hosting](./userproxies/self-hosting.md) docs to self host your own userproxies.