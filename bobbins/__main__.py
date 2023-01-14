import hikari
import lightbulb

import bobbins.checks
import bobbins.cli
import bobbins.config
import bobbins.plugin_posts

args = bobbins.cli.parser.parse_args()
if args.config:
    config = bobbins.config.load(args.config)
else:
    config = bobbins.config.load_env()


@bobbins.checks.slash_check
async def check_forum_post(ctx: lightbulb.ApplicationContext):
    channel: hikari.GuildChannel = ctx.get_channel()
    is_forum = True
    if channel.type != hikari.ChannelType.GUILD_PUBLIC_THREAD:
        is_forum = False

    elif channel.parent_id != config["forumID"]:
        is_forum = False

    if not is_forum:
        await ctx.respond(
            "You cannot use this command outside of the help forum.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    return is_forum


bobbins.post_commands.post_plugin.add_checks(check_forum_post)
bot.add_plugin(bobbins.post_commands.post_plugin)

bobbins.history.recent_posts_plugin.help_forum_id = config["forumID"]
bot.add_plugin(bobbins.history.recent_posts_plugin)


bot.run()
