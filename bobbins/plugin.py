import typing as t

import hikari
import lightbulb
from lightbulb.plugins import ListenerT

from bobbins.bot import Bot


class Plugin(lightbulb.Plugin):
    def bound_listener(
        self, event: t.Type[hikari.Event], listener_func: ListenerT | None = None
    ) -> ListenerT:
        return self.listener(event, listener_func, bind=True)

    @property
    def app(self) -> Bot:
        return t.cast(Bot, lightbulb.Plugin.app.__get__(self, type(self)))

    @app.setter
    def app(self, value: Bot):
        lightbulb.Plugin.app.__set__(self, value)
