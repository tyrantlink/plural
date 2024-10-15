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
