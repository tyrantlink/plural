from discord import ApplicationContext, Option, Attachment, slash_command, Embed
from src.import_handler import ImportHelpEmbed, ImportHandler
from src.helpers import send_error, chunk_string
from src.commands.base import BaseCommands
# from src.client.base import ClientBase


class ImportCommand(BaseCommands):
    @slash_command(
        name='import',
        description='import data from pluralkit or tupperbox',
        options=[
            Option(
                Attachment,
                name='file',
                description='the file to import. 4MB max',
                required=False),
            Option(
                str,
                name='file_url',
                description='url of your exported file. 4MB max',
                required=False)])
    async def slash_import(self, ctx: ApplicationContext, file: Attachment | None, file_url: str | None) -> None:
        if file is None and file_url is None:
            await ctx.response.send_message(embed=ImportHelpEmbed, ephemeral=True)
            return

        if file is not None and file_url is not None:
            await send_error(ctx, 'you can only provide one of file or file_url')
            return

        await ctx.response.defer(ephemeral=True)

        if file is not None:
            importer = await ImportHandler.from_attachment(ctx, file, self.client)

        if file_url is not None:
            importer = await ImportHandler.from_url(ctx, file_url, self.client)

        if importer is None:
            return

        success = await importer.import_to_plural(ctx)

        title, color = (
            ('import successful!', 0x69ff69)
            if success
            else
            ('import failed!', 0xff6969)
        )

        log = '\n'.join(importer.log) or 'no logs, everything went smoothly!'

        chunks = chunk_string(log, 4088)

        embeds = [
            Embed(
                title=title + f' ({i + 1}/{len(chunks)})',
                description=f'```{chunk}```',
                color=color
            )
            for i, chunk in enumerate(chunks)
        ] if len(chunks) > 1 else [
            Embed(
                title=title,
                description=f'```{chunks[0]}```',
                color=color
            )
        ]

        await ctx.followup.send(embeds=embeds, ephemeral=True)
