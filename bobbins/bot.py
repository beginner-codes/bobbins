import hikari
import lightbulb

import bobbins.cli
import bobbins.config
import bobbins.database


class Bot(lightbulb.BotApp):
    config: bobbins.config.ConfigDict

    def __init__(self, *args, **kwargs):
        self.config = self._load_config()
        self.db = bobbins.database.Database(
            self.config.get("DATABASE", "sqlite+aiosqlite:///")
        )
        super().__init__(token=self.config["token"], *args, **kwargs)

        self.listen(hikari.StartedEvent, self.on_started)
        self.listen(hikari.StoppedEvent, self.on_stopped)


    async def on_started(self, _):
        await self.db.connect()

    async def on_stopped(self, _):
        await self.db.disconnect()
    @staticmethod
    def _load_config() -> bobbins.config.ConfigDict:
        args = bobbins.cli.parser.parse_args()
        if args.config:
            return bobbins.config.load(args.config)

        return bobbins.config.load_env()
