from discord import Embed, EmbedField


# ? zero-width spaces to stop discord stupid list formatting looking like shit in embeds
ImportHelpEmbed = Embed(
    title='how to import data',
    color=0x69ff69,
    fields=[
        EmbedField(
            name='pluralkit',
            value='\n'.join([
                '​1. start a DM with pluralkit',
                '​2. send `pk;export` and copy the link it DMs you',
                '​3. use the `/import` command and paste the link to the `file_url` parameter']),
            inline=False
        ),
        EmbedField(
            name='tupperbox',
            value='\n'.join([
                '​1. start a DM with tupperbox',
                '​2. send `tul!export` and copy the link it DMs you',
                '​3. use the `/import` command and paste the link to the `file_url` parameter']),
            inline=False
        )
    ]
)


HelpEmbed = Embed(
    title='welcome to /plu/ral!',
    color=0x69ff69,
    fields=[
        EmbedField(
            name='getting started',
            value='\n'.join([
                '- if you\'re coming from pluralkit or tupperbox, use the `/import` command and use your proxies as you have been',
                '- otherwise, you can start by creating a new group with `/group create`',
                '  - if you don\'t create a group, a group named "default" will be created for you when you create a member',
                '- create a new member with `/member new`',
                '  - all members *must* be a part of a group, specify in the `/member new` command, or leave it blank to use the default group',
                '- add some proxy tags with `/member proxy add`',
                '- that\'s all the basics, otherwise, simply type `/` and see what commands are available!']),
            inline=False
        ),
        EmbedField(
            name='info and support',
            value='\n'.join([
                '- for more information, check out the [github](https://github.com/tyrantlink/plural)',
                '- for support, join the [discord](https://discord.gg/6t8V4Cv)',
                '- for bugs, suggestions, or other feedback, open an issue on the github']),
            inline=False
        )
    ]
)
