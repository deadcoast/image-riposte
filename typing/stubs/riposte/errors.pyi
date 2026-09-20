# Source-derived external stub; see typing/README.md for scope.
def safe_code(value: object) -> str: ...

class RiposteError(Exception):
    code: str

    def __init__(self, code: str) -> None: ...
