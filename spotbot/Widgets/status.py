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
        self._entries[key] = (keymsg, key_style, value, value_style)

    def update_entry(
        self,
        key: str,
        value: Union[RenderableType, Callable] = None,
        key_style: StyleType = None,
        value_style: StyleType = None,
    ) -> None:
        """update a status as a key/value with styles for formatting.

        Parameters
        ----------
        key : str
            Reference for the status (not shown)
        value : Union[RenderableType, Callable], optional
            Value or Value generator (called every second), by default None which
            would not change the exiting value (good for changing styling only)
        key_style : StyleType, optional
            style for the key, by default None which leave the styling the way it was
            initally set.
        value_style : StyleType, optional
            style for the value, by default None which leave the styling the way it was
            initally set.
        """
        (keymsg, old_key_style, old_value, old_value_style) = self._entries[key]
        if value is None:
            value = old_value
        if key_style is None:
            key_style = old_key_style
        if value_style is None:
            value_style = old_value_style
        self._entries[key] = (keymsg, key_style, value, value_style)

    def render(self) -> Panel:
        if self.regenerate_status_from_dict is True:
            # build the text container
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
