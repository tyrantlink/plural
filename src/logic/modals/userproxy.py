from src.discord import modal, TextInput, Interaction, TextInputStyle, MessageFlag


@modal(
    custom_id='umodal_send',
    text_inputs=[
        TextInput(
            custom_id='message',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='message',
            required=True)])
async def umodal_send(
    interaction: Interaction,
    message: str
) -> None:
    await interaction.response.send_message(
        content=message,
        flags=MessageFlag.NONE
    )


@modal(
    custom_id='umodal_edit',
    text_inputs=[
        TextInput(
            custom_id='message',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='message',
            required=True)])
async def umodal_edit(
    interaction: Interaction,
    message_id: str,
    message: str
) -> None:
    await interaction.response.edit_message(
        int(message_id),
        content=message
    )
