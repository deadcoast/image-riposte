"""Error codes, never decoder messages, source paths, or source metadata."""
class RiposteError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
