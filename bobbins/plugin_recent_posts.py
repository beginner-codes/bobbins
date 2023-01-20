import asyncio
from collections import defaultdict
from typing import cast, Generator, Iterable, TypeAlias

import hikari
import lightbulb
from hikari.events import channel_events

from bobbins.plugin import Plugin

GuildID: TypeAlias = int
UserID: TypeAlias = int
PostID: TypeAlias = int
GuildIndex: TypeAlias = dict[UserID, set[PostID]]
GuildIndexes: TypeAlias = dict[GuildID, GuildIndex]


class RecentPostsPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guild_indexes: GuildIndexes = defaultdict(_create_guild_index)


def _create_guild_index() -> GuildIndex:
    return defaultdict(set)


recent_posts_plugin = RecentPostsPlugin("Recent Posts")


@recent_posts_plugin.bound_listener(hikari.MemberDeleteEvent)
async def on_member_leave(plugin: RecentPostsPlugin, event: hikari.MemberDeleteEvent):
    if event.user.id not in plugin.guild_indexes[event.guild_id]:
        return

    await _close_open_posts(event.get_guild(), event.user, plugin.guild_indexes)
    _clear_guild_index_for_user(event.guild_id, event.user, plugin.guild_indexes)


async def _close_open_posts(
    guild: hikari.Guild, user: hikari.User, indexes: GuildIndexes
):
    tasks = []
    for post_id in indexes[guild.id][user.id]:
        post: hikari.GuildThreadChannel = cast(
            hikari.GuildThreadChannel, await guild.appNp.rest.fetch_channel(post_id)
        )
        if post.is_archived:
            continue

        tasks.append(_close_post(post))

    await asyncio.gather(*tasks)


async def _close_post(post: hikari.GuildThreadChannel):
    await post.send("ℹ️ The member has left the server. Closing post.")
    await asyncio.sleep(5)
    await post.app.rest.edit_channel(post, archived=True, locked=True)


def _clear_guild_index_for_user(
    guild_id: GuildID, user: hikari.User, indexes: GuildIndexes
):
    del indexes[guild_id][user.id]


@recent_posts_plugin.bound_listener(channel_events.GuildThreadCreateEvent)
async def on_thread_created(
    plugin: RecentPostsPlugin, event: channel_events.GuildThreadCreateEvent
):
    if event.thread.parent_id != plugin.app.config["forumID"]:
        return

    plugin.guild_indexes[event.guild_id][event.thread.owner_id].add(event.thread.id)


@recent_posts_plugin.bound_listener(channel_events.GuildThreadUpdateEvent)
async def on_thread_updated(
    plugin: RecentPostsPlugin, event: channel_events.GuildThreadCreateEvent
):
    if event.thread.parent_id != plugin.app.config["forumID"]:
        return

    users_posts = plugin.guild_indexes[event.guild_id][event.thread.owner_id]
    if event.thread.id in users_posts and event.thread.is_archived:
        users_posts.remove(event.thread.id)

    elif event.thread.id not in users_posts and not event.thread.is_archived:
        users_posts.add(event.thread.id)


@recent_posts_plugin.bound_listener(channel_events.GuildThreadDeleteEvent)
async def on_thread_deleted(
    plugin: RecentPostsPlugin, event: channel_events.GuildThreadDeleteEvent
):
    if event.thread.parent_id != plugin.app.config["forumID"]:
        return

    plugin.guild_indexes[event.guild_id][event.thread.owner_id].remove(event.thread.id)


@recent_posts_plugin.bound_listener(hikari.GuildAvailableEvent)
async def on_guild_available(
    plugin: RecentPostsPlugin, event: hikari.GuildAvailableEvent
):
    guild = event.guild
    forum_id = plugin.app.config["forumID"]

    active_posts = await guild.app.rest.fetch_active_threads(guild)
    plugin.guild_indexes[guild.id] = _build_guild_index(
        _filter_forum_posts(forum_id, active_posts)
    )


def _filter_forum_posts(
    forum_id: int, posts: Iterable[hikari.GuildThreadChannel]
) -> Generator[hikari.GuildThreadChannel, None, None]:
    for post in posts:
        if post.parent_id == forum_id:
            yield post


def _build_guild_index(active_posts: Iterable[hikari.GuildThreadChannel]) -> GuildIndex:
    index = _create_guild_index()
    for post in active_posts:
        index[post.owner_id].add(post.id)

    return index


@recent_posts_plugin.listener(hikari.GuildLeaveEvent)
async def on_guild_leave(event: hikari.GuildLeaveEvent):
    del recent_posts_plugin.guild_indexes[event.guild_id]


@recent_posts_plugin.command
@lightbulb.option(
    "user",
    "The name of the user to get the post history for",
    type=hikari.User,
    required=False,
)
@lightbulb.command("posts", "Shows a user's recent help post history")
@lightbulb.implements(lightbulb.SlashCommand)
async def posts(ctx: lightbulb.SlashContext):
    user = ctx.user
    ephemeral = True
    if ctx.options.user is not None:
        user = ctx.options.user
        ephemeral = False

    await _show_posts_history(ctx, user, ephemeral)


@recent_posts_plugin.command
@lightbulb.command("Recent Help Posts", "Shows a user's recent help post history")
@lightbulb.implements(lightbulb.UserCommand)
async def user_menu_posts_list(ctx: lightbulb.UserContext):
    await _show_posts_history(
        ctx, ctx.options.target.user, ctx.user.id == ctx.options.target.user.id
    )


async def _show_posts_history(
    ctx: lightbulb.ApplicationContext | lightbulb.UserContext,
    user: hikari.User,
    ephemeral: bool,
) -> None:
    flags = hikari.MessageFlag.EPHEMERAL if ephemeral else hikari.MessageFlag.NONE
    message = f"{user.mention} has no recent help posts in <#{recent_posts_plugin.app.config['forumID']}>."
    if (
        ctx.guild_id in recent_posts_plugin.guild_indexes
        and user.id in recent_posts_plugin.guild_indexes[ctx.guild_id]
    ):
        post_history = recent_posts_plugin.guild_indexes[ctx.guild_id][user.id]
        post_list = "\n-".join(
            f"<#{post_id}>" for post_id in sorted(post_history, reverse=True)[:10]
        )
        message = f"{user.mention} has recently opened these help posts:\n-{post_list}"

    await ctx.respond(message, flags=flags)
