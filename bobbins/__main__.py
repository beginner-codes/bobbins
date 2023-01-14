import hikari
import lightbulb

import bobbins.cli
import bobbins.config

args = bobbins.cli.parser.parse_args()
if args.config:
    config = bobbins.config.load(args.config)
else:
    config = bobbins.config.load_env()


bot = lightbulb.BotApp(token=config["token"])
bot.run()
