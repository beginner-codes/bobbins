import argparse
import pathlib


parser = argparse.ArgumentParser(
    prog="Bobbins the Discord Bot",
    description="Bobbins is a bot that manages help posts in a Discord forum.",
)
parser.add_argument(
    "-c",
    "--config",
    help="File that should be used for configuring the bot.",
    metavar="FILE.json",
    type=pathlib.Path,
)
