# /plu/ral
**Add /plu/ral to your server: https://plural.gg/invite**

/plu/ral is a plural/roleplay proxy Discord bot built to modern discord app standards, using slash commands and interactions, including autocomplete for member and group names, and an interactive message command for editing, so no more copying your entire message to edit.

Made to be a simpler alternative to PluralKit and Tupperbox, no profiles, no public information, just groups, members, and proxies, and with the implementation of the new Discord features, there's no need for a web dashboard, everything can easily be done in Discord. If you're coming from PluralKit or Tupperbox, you can import your existing data with a single command.

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
- Restrict a group to certain channels, with roleplay proxies for example, with `/group channels add`
- And a fully featured API, anything you can do with the bot, you can do with the API https://api.plural.gg/docs

# Hosting and development
If you don't plan on hosting it yourself, you can simply add the bot with https://plural.gg/invite and stop reading here.

for hosting or local development, you'll need the following:
- Podman/Docker
- A Discord bot token

### Instructions
```sh
git clone https://github.com/tyrantlink/plural
cd plural
cp .env.example .env
# Edit .env with your bot token
podman compose up --no-recreate -d # or docker-compose up --no-recreate -d
```

# License
This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details