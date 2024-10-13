from discord import Interaction, ApplicationContext, Embed, Colour, MessageReference, Message, User, Member, HTTPException, Forbidden
from discord.ui import Modal as _Modal, InputText, View as _View, Item
from asyncio import sleep, create_task
from functools import partial


class CustomModal(_Modal):
    def __init__(self, title: str, children: list[InputText]) -> None:
        super().__init__(*children, title=title)

    async def callback(self, interaction: Interaction):
        self.interaction = interaction
        self.stop()


class View(_View):
    def __init__(
        self,
        *items: Item,
        timeout: float | None = None,
        disable_on_timeout: bool = False
    ) -> None:
        # ? black magic to stop the view from adding all items on creation and breaking when there's too many
        # ? but still register the attributes as items, mypy is not happy
        tmp, self.__view_children_items__ = self.__view_children_items__, []  # type: ignore
        super().__init__(*items, timeout=timeout, disable_on_timeout=disable_on_timeout)
        self.__view_children_items__ = tmp  # type: ignore

        for func in self.__view_children_items__:
            item: Item = func.__discord_ui_model_type__(  # type: ignore
                **func.__discord_ui_model_kwargs__)  # type: ignore
            item.callback = partial(func, self, item)  # type: ignore
            item._view = self
            setattr(self, func.__name__, item)


class ErrorEmbed(Embed):
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = 'error'
        self.description = message
        self.colour = Colour(0xff6969)


class SuccessEmbed(Embed):
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = 'success'
        self.description = message
        self.colour = Colour(0x69ff69)


async def send_error(ctx: ApplicationContext | Interaction, message: str) -> None:
    if ctx.response.is_done():
        await ctx.followup.send(
            embed=ErrorEmbed(message),
            ephemeral=True
        )
        return

    await ctx.response.send_message(
        embed=ErrorEmbed(message),
        ephemeral=True
    )


async def send_success(ctx: ApplicationContext | Interaction, message: str) -> None:
    if ctx.response.is_done():
        await ctx.followup.send(
            embed=SuccessEmbed(message),
            ephemeral=True
        )
        return

    await ctx.response.send_message(
        embed=SuccessEmbed(message),
        ephemeral=True
    )


def chunk_string(string: str, chunk_size: int) -> list[str]:
    lines = string.split('\n')

    for i, _ in enumerate(lines):
        if len(lines[i]) > chunk_size:
            raise ValueError(
                f'line {i} is too long ({len(lines[i])}/{chunk_size})')

    chunks = []
    chunk = ''
    for line in lines:
        if len(chunk) + len(line) > chunk_size:
            chunks.append(chunk)
            chunk = ''

        chunk += f'{'\n' if chunk else ''}{line}'

    if chunk:
        chunks.append(chunk)

    return chunks


async def __notify(
    message: Message,
    reaction: str = '❌',
    delay: int | float = 1
) -> None:
    if message._state.user is None:
        return  # ? should never be none but mypy is stupid

    try:
        await message.add_reaction(reaction)
        await sleep(delay)
        await message.remove_reaction(reaction, message._state.user)
    except (HTTPException, Forbidden):
        pass


def notify(
    message: Message,
    reaction: str = '❌',
    delay: int | float = 1
) -> None:
    create_task(__notify(message, reaction, delay))


def format_reply(content: str, reference: MessageReference | None) -> str:
    if reference is None:
        return content

    if not isinstance(reference.resolved, Message):
        return content

    refcontent = reference.resolved.content.replace('\n', ' ')
    refattachments = reference.resolved.attachments
    mention = (
        reference.resolved.author.mention
        if reference.resolved.webhook_id is None else
        f'@{reference.resolved.author.name}'
    )

    base_reply = (
        f'-# [↪](<{reference.resolved.jump_url}>) {mention}')

    formatted_refcontent = (
        refcontent
        if len(refcontent) <= 75 else
        f'{refcontent[:75].strip()}…'
    )

    reply_content = (
        formatted_refcontent
        if formatted_refcontent else
        f'[*Click to see attachment*](<{reference.resolved.jump_url}>)'
        if refattachments else
        f'[*Click to see message*](<{reference.resolved.jump_url}>)'
    )

    # ? currently doing without jump as i think i looks better,
    # ? leaving this here if i change my mind or think of a better implementation
    # f'{base_reply} [{reply_content}](<{reference.resolved.jump_url}>)\n{content}'
    return f'{base_reply} {reply_content}\n{content}'
