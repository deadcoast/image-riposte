# Source-derived external stub; see typing/README.md for scope.
from .surface import Surface as Surface
LOGO: tuple[str, ...]

def counterstroke(surface: Surface, x: int, y: int, width: int, height: int, time: float, active: bool=False) -> None: ...

def activity_trace(surface: Surface, x: int, y: int, width: int, time: float, state: str='RUNNING') -> None: ...
