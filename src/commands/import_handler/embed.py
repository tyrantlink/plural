from discord import Embed


ImportHelpEmbed = Embed(
    title='how to import data',
    color=0x69ff69
)


# ? zero-width spaces to stop discord stupid list formatting looking like shit in embeds

ImportHelpEmbed.add_field(
    name='pluralkit',
    value='\n'.join([
        '​1. start a DM with pluralkit',
        '​2. send `pk;export`',
        '​3. download the file, or copy the link',
        '​4. use the `/import` command and upload the file or paste the link']),
    inline=False
)


ImportHelpEmbed.add_field(
    name='tupperbox',
    value='\n'.join([
        '​1. start a DM with tupperbox',
        '​2. send `tul!export`',
        '​3. download the file, or copy the link',
        '​4. use the `/import` command and upload the file or paste the link']),
    inline=False
)
