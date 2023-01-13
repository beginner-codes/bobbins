# Bobbins

Bobbins is a bot that you can use in your Discord community server to manage help posts in a forum.

## Installation

1. Clone this repository and cd into the folder that was created.
2. Run `poetry install` to get all the dependencies you need to run the bot.
2. Make a copy of `example-config.json`. In the copy you made add:
  a. Your bot token
  b. The ID of the forum channel
3. To start the bot run `poetry run python -m bobbins -c config.json`
  - *Replace `config.json` with the name of your config file.*

