import hikari
import lightbulb


def check(func) -> lightbulb.checks.Check:
    return lightbulb.checks.Check(func)


@check
async def threads_only(ctx: lightbulb.ApplicationContext):
    if ctx.command.name == "help":
        return True

    match ctx.get_channel():
        case hikari.GuildThreadChannel():
            return True

        case _:
            await ctx.respond(
                "You cannot use this command outside of a thread.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return False
