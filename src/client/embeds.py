from discord import Embed, Message


class ReplyEmbed(Embed):
    def __init__(self, message: Message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_author(
            name=f'{message.author.display_name} ↩️',
            icon_url=message.author.display_avatar.url
        )
        self.description = (
            (  # ? i hate this autoformatter sometimes
                f'**[Reply to:] ({message.jump_url})**{message.content[:100]}{'…' if len(message.content) > 100 else ""}')
            if message.content else
            (
                f'*[(click to see attachment{"" if len(message.attachments)-1 else "s"})]({message.jump_url})*')
            if message.attachments else
            f'*[click to see message]({message.jump_url})*'
        )
