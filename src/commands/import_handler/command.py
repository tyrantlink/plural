from discord import ApplicationContext, Option, Attachment, slash_command, Embed
from src.commands.base import BaseCommands
from src.helpers import send_error
from .embed import ImportHelpEmbed
from .importer import Importer


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
            importer = await Importer.from_attachment(ctx, file)

        if file_url is not None:
            importer = await Importer.from_url(ctx, file_url)

        if importer is None:
            return

        success = await importer.import_to_plural(ctx, self.client.db)

        log = '\n'.join(importer.log) or 'no logs, everything went smoothly!'

        embed = Embed(description=f'```{log}```')

        if success:
            embed.title = 'import successful!'
            embed.color = 0x69ff69
        else:
            embed.title = 'import failed!'
            embed.color = 0xff6969

        await ctx.followup.send(embed=embed, ephemeral=True)