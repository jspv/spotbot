from textual import events
from textual import log
from textual.reactive import Reactive
from textual.widgets import Static
from rich.text import Text
from rich.style import StyleType, Style
from rich.padding import Padding
from rich.console import RenderableType
from typing import Union, Callable


class Status(Static):

    # Hold dict of statuses to report on
    _entries = {}
    message: RenderableType | None = None
    _regenerate_status_from_dict: Reactive(bool) = Reactive(False)
    status_stack = []  # stack of status settings

    COMPONENT_CLASSES = {
        "status--highlight-key-style",
        "status--highlight-value-style",
        "status--key-style",
        "status--value-style",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def on_mount(self, event: events.Mount) -> None:
        # """Refresh status every second"""
        # self.set_interval(1.0, callback=self.refresh)
        pass

    def add_entry(
        self,
        key: str,
        keymsg: RenderableType,
        value: RenderableType | Callable,
    ) -> None:
        value_style = self.get_component_rich_style("status--value-style")
        key_style = self.get_component_rich_style("status--key-style")
        self._entries[key] = (keymsg, key_style, value, value_style)

    def update_entry(
        self,
        key: str,
        value: RenderableType | Callable = None,
        highlight_key: bool | StyleType = False,
        highlight_value: bool | StyleType = False,
    ) -> None:
        """update a status as a key/value with styles for formatting.

        Parameters
        ----------
        key : str
            Reference for the status (not shown)
        value : Union[RenderableType, Callable], optional
            Value or Value generator (called every second), by default None which
            would not change the exiting value (good for changing styling only)
        hightlight_key: bool
            Should the key/value be highlighted
        """
        (keymsg, old_keystyle, old_value, old_valstyle) = self._entries[key]

        if not isinstance(highlight_key, Style):
            value_style = (
                self.get_component_rich_style("status--highlight-value-style")
                if highlight_value is True
                else self.get_component_rich_style("status--value-style")
            )

        if not isinstance(highlight_value, Style):
            key_style = (
                self.get_component_rich_style("status--highlight-key-style")
                if highlight_key is True
                else self.get_component_rich_style("status--value-style")
            )

        if value is None:
            value = old_value

        self._entries[key] = (keymsg, key_style, value, value_style)

    def update_status(self) -> None:
        self._regenerate_status_from_dict = True

    def render(self) -> RenderableType:
        if self._regenerate_status_from_dict is True or self.message is None:
            # build the text container
            self.message = Text(
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
                    self.message.append(" | ")
                count += 1
                # If it's a str, treat it as markup
                if isinstance(keymsg, str):
                    self.message.append_text(Text.from_markup(keymsg, style=key_style))
                else:
                    self.message.append_text(keymsg)
                self.message.append(": ")
                if isinstance(value, Callable):
                    value = value()
                if isinstance(value, str):
                    value = Text.from_markup(value, style=value_style)
                self.message.append_text(value)
        self._regenerate_status_from_dict = False
        return Padding(self.message, pad=(0, 1, 0, 2), expand=True)
