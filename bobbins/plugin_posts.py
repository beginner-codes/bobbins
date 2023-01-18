from typing import cast

import hikari
import lightbulb
import lightbulb.utils as lbutils

import bobbins.checks

post_plugin = lightbulb.Plugin("Posts")
post_plugin.add_checks(bobbins.checks.threads_only)


def _is_forum_mod(
    member: hikari.Member, channel: hikari.PermissibleGuildChannel
) -> bool:
    permissions = lbutils.permissions.permissions_in(channel, member, True)
    return permissions & hikari.Permissions.MANAGE_THREADS != hikari.Permissions.NONE


@post_plugin.command
@lightbulb.command("close", "Close your help post")
@lightbulb.implements(lightbulb.SlashCommand)
@lightbulb.decorators.add_cooldown(50, 1, lightbulb.UserBucket, lightbulb.SlidingWindowCooldownAlgorithm)
async def close(ctx: lightbulb.ApplicationContext) -> None:
    channel: hikari.GuildPublicThread = cast(
        hikari.GuildPublicThread, ctx.get_channel()
    )
    parent_channel = ctx.get_guild().get_channel(channel.parent_id)
    if not isinstance(parent_channel, hikari.PermissibleGuildChannel):
        await ctx.respond(
            "This command cannot be used here.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    if (
        not _is_forum_mod(ctx.member, parent_channel)
        and ctx.author.id != channel.owner_id
    ):
        await ctx.respond(
            "This is not your help post.", flags=hikari.MessageFlag.EPHEMERAL
        )
        return

    await ctx.respond(
        f"<@!{channel.owner_id}> this post has been closed. Feel free to reopen it if you have any further questions."
    )
    await channel.app.rest.edit_channel(channel, archived=True)


@post_plugin.command
@lightbulb.command("lock", "Locks a help post", hidden=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def lock(ctx: lightbulb.ApplicationContext) -> None:
    channel: hikari.GuildPublicThread = cast(
        hikari.GuildPublicThread, ctx.get_channel()
    )
    parent_channel = ctx.get_guild().get_channel(channel.parent_id)
    if not isinstance(parent_channel, hikari.PermissibleGuildChannel):
        await ctx.respond(
            "This command cannot be used here.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    if not _is_forum_mod(ctx.member, parent_channel):
        await ctx.respond(
            "You cannot lock posts.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    await ctx.respond(
        f"<@!{channel.owner_id}> this post has been locked by {ctx.author.mention}."
    )
    await channel.app.rest.edit_channel(channel, archived=True, locked=True)
