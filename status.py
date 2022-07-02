from textual import events
from textual.widget import Widget
from textual.reactive import Reactive
from rich.text import Text
from rich.style import StyleType
from rich.padding import Padding
from rich.panel import Panel
from rich.console import RenderableType
from typing import Union, Callable


class Status(Widget):
    def __init__(
        self,
        *args,
        style: StyleType = "yellow on default",
        title: Union[Text, str] = "",
        title_align="center",
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.style = style
        self.title = title
        self.title_align = title_align

    # The following will react automatically to changes
    style: Reactive[StyleType] = Reactive("default on default")
    title: Reactive[str] = Reactive("")
    regenerate_status_from_dict: Reactive[bool] = Reactive(True)

    # Hold dict of statuses to report on
    _entries = {}
    message: RenderableType = "none"
    status_stack = []  # stack of status settings

    async def on_mount(self, event: events.Mount) -> None:
        """Refresh status evey second"""
        self.set_interval(1.0, callback=self.refresh)

    def add_entry(
        self,
        key: str,
        keymsg: RenderableType,
        value: Union[RenderableType, Callable],
        key_style: StyleType = "none",
        value_style: StyleType = "none",
    ) -> None:
        """Add a status as a key/value with styles for formatting."""
        self._entries[key] = (keymsg, key_style, value, value_style)

    def render(self) -> Panel:
        if self.regenerate_status_from_dict is True:
            # build the renderable
            self.message = Text(
                style=self.style,
                no_wrap=True,
                overflow="ellipsis",
                justify="left",
                end="",
            )
            # Build the statuses
            count = 0
            for (keymsg, key_style, value, value_style) in self._entries.values():
                if count > 0:
                    # Print a seperator between items
                    self.message.append(" | ", self.style)
                count += 1
                self.message.append_text(Text.from_markup(keymsg, style=key_style))
                self.message.append(": ", self.style)
                if isinstance(value, Callable):
                    value = value()
                self.message.append_text(Text.from_markup(value, style=value_style))

        return Panel(
            Padding(
                self.message,
                pad=(0, 1, 0, 2),
                style=self.style,
                expand=True,
            ),
            title=self.title,
            title_align=self.title_align,
        )
