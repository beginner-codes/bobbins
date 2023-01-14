from collections import defaultdict
from typing import cast

import hikari
import lightbulb
from hikari.events import channel_events

from bobbins.plugin import Plugin


class HistoryPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history: dict[int, set[int]] = defaultdict(set)


history_plugin = HistoryPlugin("HistoryPlugin")


@history_plugin.listener(channel_events.GuildThreadCreateEvent)
async def on_new_thread_created(event: channel_events.GuildThreadCreateEvent):
    if event.thread.parent_id != history_plugin.help_forum_id:
        return

    history_plugin.history[event.thread.owner_id].add(event.thread.id)


@history_plugin.listener(hikari.StartedEvent)
async def on_bot_started(event: hikari.StartedEvent):
    forum: hikari.GuildForumChannel = cast(
        hikari.GuildForumChannel,
        await event.app.rest.fetch_channel(history_plugin.help_forum_id),
    )
    guild = forum.get_guild()
    posts = await guild.app.rest.fetch_active_threads(guild)
    for post in posts:
        if post.parent_id == history_plugin.help_forum_id:
            history_plugin.history[post.owner_id].add(post.id)


@history_plugin.command
@lightbulb.option(
    "user",
    "The name of the user to get the post history for",
    type=hikari.User,
    required=False,
)
@lightbulb.command("posts", "Shows a user's recent help post history")
@lightbulb.implements(lightbulb.SlashCommand)
async def posts(ctx: lightbulb.ApplicationContext) -> None:
    user = ctx.author
    flags = hikari.MessageFlag.EPHEMERAL
    if ctx.options.user is not None:
        user = ctx.options.user
        flags = hikari.MessageFlag.NONE

    message = (
        f"{user.mention} has no recent help posts in <#{history_plugin.help_forum_id}>."
    )
    if post_history := history_plugin.history.get(user.id):
        post_list = "\n-".join(f"<#{post_id}>" for post_id in post_history)
        message = f"{user.mention} has recently opened these help posts:\n-{post_list}"

    await ctx.respond(message, flags=flags)
