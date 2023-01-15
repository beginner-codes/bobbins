import json
import os
from pathlib import Path
from typing import TypedDict

import bobbins.exceptions

ConfigDict = TypedDict(
    "ConfigDict", {"token": str, "forumID": int | str, "database": str | None}
)


def load(config_path: Path) -> ConfigDict:
    if not config_path.exists():
        raise bobbins.exceptions.ProvidedConfigDoesNotExist(
            f"The config file {config_path} does not exist."
        )

    with config_path.open() as config_file:
        try:
            config: ConfigDict = json.load(config_file)
        except json.decoder.JSONDecodeError as exc:
            raise bobbins.exceptions.ProvidedConfigIsInvalid(
                f"The config file {config_path} is not a valid JSON file."
            ) from exc

    return _process_config(config)


def load_env() -> ConfigDict:
    config = {}
    if "DISCORD_TOKEN" not in os.environ:
        raise bobbins.exceptions.RequiredEnvironmentVariableIsNotSet(
            "The Discord bot token could not be found in the DISCORD_TOKEN environment variable."
        )

    if "DISCORD_FORUM_ID" not in os.environ:
        raise bobbins.exceptions.RequiredEnvironmentVariableIsNotSet(
            "The Discord Forum Channel ID could not be found in the DISCORD_FORUM_ID environment variable."
        )

    try:
        config = {
            "token": os.environ["DISCORD_TOKEN"],
            "forumID": int(os.environ["DISCORD_FORUM_ID"]),
            "database": os.environ.get("DATABASE_URI", None),
        }
    except ValueError as exc:
        raise bobbins.exceptions.ProvidedForumChannelIDIsInvalid(
            f"The forum channel ID {config['forumID']!r} is not a valid type for a channel ID."
        ) from exc

    return _process_config(config)


def _process_config(config: ConfigDict) -> ConfigDict:
    try:
        config["forumID"] = int(config["forumID"])
    except KeyError as exc:
        raise bobbins.exceptions.ProvidedForumChannelIDIsInvalid(
            "You must provided a help forum channel ID in your config file."
        ) from exc
    except ValueError as exc:
        raise bobbins.exceptions.ProvidedForumChannelIDIsInvalid(
            f"The forum channel ID {config['forumID']!r} is not a valid type for a channel ID."
        ) from exc

    if config.get("database", None) is None:
        config["database"] = "sqlite+aiosqlite:///bobbins.db"

    return config
