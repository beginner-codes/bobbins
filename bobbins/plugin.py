import lightbulb


class Plugin(lightbulb.Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help_forum_id = 0