import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import cast, Generator, Iterable, TypeAlias

import hikari
import lightbulb
from hikari.events import channel_events

from bobbins.plugin import Plugin

_LOGGER: logging.Logger = logging.getLogger("bobbins.recents")

GuildID: TypeAlias = int
UserID: TypeAlias = int
PostID: TypeAlias = int
GuildIndex: TypeAlias = dict[UserID, set[PostID]]
GuildIndexes: TypeAlias = dict[GuildID, GuildIndex]


class RecentPostsPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guild_indexes: GuildIndexes = defaultdict(_create_guild_index)
        self.guild_tasks: dict[int, asyncio.TimerHandle] = {}


def _create_guild_index() -> GuildIndex:
    return defaultdict(set)


recent_posts_plugin = RecentPostsPlugin("Recent Posts")


@recent_posts_plugin.bound_listener(hikari.MemberDeleteEvent)
async def on_member_leave(plugin: RecentPostsPlugin, event: hikari.MemberDeleteEvent):
    if event.user.id not in plugin.guild_indexes[event.guild_id]:
        return

    _LOGGER.debug("Member left guild, cleaning up index and closing their posts")
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

        tasks.append(
            _close_post(
                post, "ℹ️ The member has left the server. Closing post.", lock=True
            )
        )

    _LOGGER.debug(f"Closing {len(tasks)} posts because the user left")
    await asyncio.gather(*tasks)


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

    _LOGGER.debug("Add a new post to the guild index")
    plugin.guild_indexes[event.guild_id][event.thread.owner_id].add(event.thread.id)


@recent_posts_plugin.bound_listener(channel_events.GuildThreadUpdateEvent)
async def on_thread_updated(
    plugin: RecentPostsPlugin, event: channel_events.GuildThreadCreateEvent
):
    if event.thread.parent_id != plugin.app.config["forumID"]:
        return

    users_posts = plugin.guild_indexes[event.guild_id][event.thread.owner_id]
    if event.thread.id in users_posts and event.thread.is_archived:
        _LOGGER.debug("Remove a closed post from the guild index")
        users_posts.remove(event.thread.id)

    elif event.thread.id not in users_posts and not event.thread.is_archived:
        _LOGGER.debug("Add a reopened post to the guild index")
        users_posts.add(event.thread.id)


@recent_posts_plugin.bound_listener(channel_events.GuildThreadDeleteEvent)
async def on_thread_deleted(
    plugin: RecentPostsPlugin, event: channel_events.GuildThreadDeleteEvent
):
    if event.thread.parent_id != plugin.app.config["forumID"]:
        return

    _LOGGER.debug("Remove a deleted post from the guild index")
    plugin.guild_indexes[event.guild_id][event.thread.owner_id].remove(event.thread.id)


@recent_posts_plugin.bound_listener(hikari.GuildAvailableEvent)
async def on_guild_available(
    plugin: RecentPostsPlugin, event: hikari.GuildAvailableEvent
):
    guild = event.guild
    forum_id = plugin.app.config["forumID"]

    _LOGGER.info(
        f"{guild.name!r} is now available: building index and scheduling post closings"
    )
    active_posts = await guild.app.rest.fetch_active_threads(guild)
    plugin.guild_indexes[guild.id] = _build_guild_index(
        _filter_forum_posts(forum_id, active_posts)
    )

    await _schedule_next_archive(_filter_forum_posts(forum_id, active_posts))


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


async def _schedule_next_archive(posts: Iterable[hikari.GuildThreadChannel]):
    next_post = None
    next_post_last_messaged = timedelta(days=0)
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    message = (
        "ℹ️ This post has been inactive for 7 days. {mention} feel free to reclaim this channel if you have any "
        "further questions."
    )
    for post in posts:
        try:
            last_message = await post.fetch_message(post.last_message_id)
        except hikari.errors.NotFoundError:
            _LOGGER.info(f"{post.name!r} has no messages?")
            last_messaged = now - post.created_at
        else:
            last_messaged = now - last_message.created_at

        if last_messaged > timedelta(days=7):
            _LOGGER.info(
                f"Closing {post.name!r} in {post.get_guild().name!r} because it's too old"
            )
            await _close_post(
                post,
                message.format(mention=f"<@{post.owner_id}>"),
            )

        elif (
            next_post is None or now - last_message.created_at < next_post_last_messaged
        ):
            next_post = post
            next_post_last_messaged = now - last_message.created_at

    if next_post is not None:
        _archive_post(
            next_post,
            timedelta(days=7) - next_post_last_messaged,
            message.format(mention=f"<@{next_post.owner_id}>"),
        )


def _archive_post(post: hikari.GuildThreadChannel, when: timedelta, message: str):
    loop = asyncio.get_running_loop()

    async def schedule():
        forum_id = recent_posts_plugin.app.config["forumID"]

        guild = post.get_guild()
        active_posts = await guild.app.rest.fetch_active_threads(guild)
        await _schedule_next_archive(_filter_forum_posts(forum_id, active_posts))

    def callback():
        task = _close_post(
            post,
        )
        loop.create_task(task)
        loop.create_task(schedule())

    _LOGGER.info(f"Scheduling to close {post.name!r} in {when}")
    timer = loop.call_at(when.total_seconds(), callback)
    recent_posts_plugin.guild_tasks[post.guild_id] = timer


@recent_posts_plugin.listener(hikari.GuildLeaveEvent)
async def on_guild_leave(event: hikari.GuildLeaveEvent):
    _LOGGER.info(f"Left guild {event.old_guild.name!r}, cleaning up index")
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
async def posts_command(ctx: lightbulb.SlashContext):
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


async def _close_post(
    post: hikari.GuildThreadChannel, message: str, *, lock: bool = False
):
    _LOGGER.debug(f"Closing {post.name!r}")
    await post.send(message)
    await asyncio.sleep(5)
    await post.app.rest.edit_channel(post, archived=True, locked=lock)
