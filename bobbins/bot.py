import lightbulb

import bobbins.cli
import bobbins.config


class Bot(lightbulb.BotApp):
    config: bobbins.config.ConfigDict

    def __init__(self, *args, **kwargs):
        self.config = self._load_config()
        super().__init__(token=self.config["token"], *args, **kwargs)

    @staticmethod
    def _load_config() -> bobbins.config.ConfigDict:
        args = bobbins.cli.parser.parse_args()
        if args.config:
            return bobbins.config.load(args.config)

        return bobbins.config.load_env()
