from textual.widget import Widget
from rich.panel import Panel
from rich.text import Text
from rich.style import StyleType
from typing import Union


class Body(Widget):
    def __init__(
        self,
        *args,
        style: StyleType = "yellow on default",
        title: Union[Text, str] = "",
        title_align: str = "center",
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

    def render(self) -> Panel:
        return Panel(
            "[b]This[/b] is the body of my application",
        )
