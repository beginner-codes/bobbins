import logging
from types import MethodType
from typing import Callable

import hikari
import lightbulb
import lightbulb.utils as lbutils

import bobbins.cli
import bobbins.config
import bobbins.database

_LOGGER: logging.Logger = logging.getLogger("bobbins")


class Bot(lightbulb.BotApp):
    config: bobbins.config.ConfigDict

    def __init__(self, *args, **kwargs):
        self.config = self._load_config()
        self.db = bobbins.database.Database(self.config["database"])
        self.__db_failure = False
        super().__init__(token=self.config["token"], *args, **kwargs)

        self.listen(hikari.StartedEvent)(self.on_started)
        self.listen(hikari.StoppedEvent)(self.on_stopped)
        self.command(self.admin_setup, True)

    def command(
        self,
        cmd_like: lightbulb.commands.base.CommandLike | None = None,
        bind: bool = False,
    ) -> lightbulb.commands.base.CommandLike | Callable[
        [lightbulb.commands.base.CommandLike], lightbulb.commands.base.CommandLike
    ]:
        cmd = super().command(cmd_like)
        if bind:
            cmd.callback = MethodType(cmd.callback, self)

        return cmd

    async def on_started(self, _):
        try:
            await self.db.connect()
            _LOGGER.info(f"Connected {self.db}")
        except Exception:
            self.__db_failure = True
            raise

    async def on_stopped(self, _):
        await self.db.disconnect()

    @lightbulb.command(
        "admin-setup",
        "Update the bot's database",
        guilds=(644299523686006834,),
        ephemeral=True,
        hidden=True,
    )
    @lightbulb.implements(lightbulb.SlashCommand)
    async def admin_setup(self, ctx: lightbulb.SlashContext):
        if (
            not ctx.member
            or not lbutils.permissions_for(ctx.member) & hikari.Permissions.MANAGE_GUILD
        ):
            await ctx.respond(
                "You do not have the necessary permissions to use this command."
            )
            return

        if self.__db_failure:
            await ctx.respond(
                f"⚠️ **Critical Failure** ⚠️\nThe database failed to connect."
            )
            return

        try:
            await self.db.update_tables()
        except Exception as exc:
            await ctx.respond(f"⚠️ **Critical Failure** ⚠️\n```\n{exc}\n```")
            raise
        else:
            await ctx.respond("The Bobbins database tables have been updated")

    @staticmethod
    def _load_config() -> bobbins.config.ConfigDict:
        args = bobbins.cli.parser.parse_args()
        if args.config:
            return bobbins.config.load(args.config)

        return bobbins.config.load_env()
