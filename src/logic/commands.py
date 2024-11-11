from src.discord import slash_command, Interaction


@slash_command(
    name='ping', description='check the bot\'s latency')
async def test_command(interaction: Interaction):
    await interaction.response.send_message('pong!')


@slash_command(
    name='ping6', description='check the bot\'s latency 6')
async def test_command6(interaction: Interaction):
    await interaction.response.send_message('pong6!')
