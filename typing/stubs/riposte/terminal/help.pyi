# Source-derived external stub; see typing/README.md for scope.
from typer._click import Context, HelpFormatter
from typer.core import TyperCommand, TyperGroup

def format_help(command: TyperCommand | TyperGroup, ctx: Context, formatter: HelpFormatter) -> None: ...

class RichCommand(TyperCommand):

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None: ...

class RichGroup(TyperGroup):

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None: ...
