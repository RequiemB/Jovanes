from discord.ext.commands.errors import CommandError

from typing import Any

class EntityDisabled(CommandError): 
    def __init__(self, _type: Any) -> None:
        self.type = _type
