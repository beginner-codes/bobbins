import hikari

import bobbins.bot
import bobbins.plugin_posts
import bobbins.plugin_recent_posts

bot = bobbins.bot.Bot(
    help_slash_command=True,
    intents=hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS,
)
bot.add_plugin(bobbins.plugin_posts.post_plugin)
bot.add_plugin(bobbins.plugin_recent_posts.recent_posts_plugin)
bot.run()
