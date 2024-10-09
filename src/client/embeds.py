from discord import Embed, Message


class ReplyEmbed(Embed):
    # ? this is only here as a fallback if a message is too long for inline reply
    def __init__(self, message: Message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_author(
            name=f'{message.author.display_name} ↩️',
            icon_url=message.author.display_avatar.url
        )

        content = message.content.replace('\n', ' ')

        formatted_content = (
            content
            if len(content) <= 75 else
            f'{content[:75].strip()}…'
        )

        self.description = (
            (  # ? i hate this autoformatter sometimes
                f'**[Reply to:]({message.jump_url})** {formatted_content}')
            if message.content else
            (
                f'*[(click to see attachment{"" if len(message.attachments)-1 else "s"})]({message.jump_url})*')
            if message.attachments else
            f'*[click to see message]({message.jump_url})*'
        )
