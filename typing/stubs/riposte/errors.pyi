# Source-derived external stub; see typing/README.md for scope.
class RiposteError(Exception):
    code: str

    def __init__(self, code: str) -> None: ...
