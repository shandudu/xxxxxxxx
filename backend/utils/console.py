from rich.console import Console


class CustomConsole(Console):
    """自定义控制台"""

    def _symbol(self, symbol: str, fallback: str) -> str:
        """Return an ASCII marker when the active Windows code page cannot encode a symbol."""
        encoding = getattr(self.file, 'encoding', None) or 'utf-8'
        try:
            symbol.encode(encoding)
        except (LookupError, UnicodeEncodeError):
            return fallback
        return symbol

    def note(self, msg: str) -> None:
        """输出注释"""
        self.print(f'[bold white]{self._symbol("•", "*")}[/] [white]{msg}[/]')

    def info(self, msg: str) -> None:
        """输出信息"""
        self.print(f'[bold cyan]{self._symbol("•", "*")}[/] {msg}')

    def tip(self, msg: str) -> None:
        """输出提示消息"""
        self.print(f'[bold green]{self._symbol("✓", "OK")}[/] [green]{msg}[/]')

    def warning(self, msg: str) -> None:
        """输出警告消息"""
        self.print(f'[bold yellow]{self._symbol("⚠", "!")}[/] [yellow]{msg}[/]')

    def caution(self, msg: str) -> None:
        """输出危险消息"""
        self.print(f'[bold red]{self._symbol("✗", "X")}[/] [red]{msg}[/]')


console = CustomConsole()
