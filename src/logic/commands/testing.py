from src.discord import slash_command, Interaction
from asyncio import sleep


@slash_command(
    name='ping', description='check the bot\'s latency')
async def test_command(interaction: Interaction):
    await interaction.response.send_message('pong!')

    await sleep(5)

    await interaction.followup.send('followup pong!')


@slash_command(
    name='ping6', description='check the bot\'s latency 6')
async def test_command6(interaction: Interaction):
    await interaction.response.send_message('pong6!')
