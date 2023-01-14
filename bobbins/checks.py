import lightbulb


def slash_check(func) -> lightbulb.checks.Check:
    return lightbulb.checks.Check(func)
