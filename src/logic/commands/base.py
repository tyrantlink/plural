from src.discord import slash_command, Interaction, SlashCommandGroup
from time import time


@slash_command(
    name='ping', description='check the bot\'s latency')
async def slash_ping(interaction: Interaction):
    timestamp = (interaction.id >> 22) + 1420070400000

    await interaction.response.send_message(
        f'pong! ({round((time()*1000-timestamp))}ms)'
    )


test = SlashCommandGroup(
    name='test', description='test commands'
)


@test.command(
    name='subcommand', description='test subcommand')
async def slash_test_subcommand(interaction: Interaction):
    await interaction.response.send_message('subcommand')

test2 = SlashCommandGroup(
    name='test2', description='test commands 2'
)

test3 = test2.create_subgroup(
    name='test3', description='test commands 3'
)


@test3.command(
    name='subcommand', description='test subcommand')
async def slash_test2_test3_subcommand(interaction: Interaction):
    await interaction.response.send_message('subcommand2')


@test3.command(
    name='subcommand2', description='test subcommand 2')
async def slash_test2_test3_subcommand2(interaction: Interaction):
    await interaction.response.send_message('subcommand3')
