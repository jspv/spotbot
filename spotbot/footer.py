from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
import rich.repr

from textual import events
from textual.reactive import Reactive
from textual.widget import Widget


@rich.repr.auto
class Footer(Widget):
    def __init__(
        self,
        *args,
        key_style="bold green on default",
        key_hover_style="bold green reverse",
        key_description_style="white on default",
        **kwargs,
    ) -> None:
        self.keys: list[tuple[str, str]] = []
        super().__init__(*args, **kwargs)
        self.layout_size = 1
        self.key_style = key_style
        self.key_hover_style = key_hover_style
        self.key_description_style = key_description_style
        self._key_text: Text | None = None

    highlight_key: Reactive[str | None] = Reactive(None)
    # _key_text: Reactive[RenderableType | None] = Reactive(non)

    async def watch_highlight_key(self, value) -> None:
        """If highlight key changes we need to regenerate the text."""
        self._key_text = None

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        """Store any key we are moving over."""
        self.highlight_key = event.style.meta.get("key")

    async def on_leave(self, event: events.Leave) -> None:
        """Clear any highlight when the mouse leave the widget"""
        self.highlight_key = None

    def __rich_repr__(self) -> rich.repr.Result:
        yield "keys", self.keys

    def make_key_text(self) -> Text:
        """Create text containing all the keys."""
        text = Text(
            style=self.style,
            no_wrap=True,
            overflow="ellipsis",
            justify="left",
            end="",
        )
        for binding in self.app.bindings.shown_keys:
            key_display = (
                binding.key.upper()
                if binding.key_display is None
                else binding.key_display
            )
            hovered = self.highlight_key == binding.key
            key_text = Text.assemble(
                (
                    f" ({key_display}) ",
                    self.key_hover_style if hovered else self.key_style,
                ),
                (f" {binding.description} ", self.key_description_style),
                meta={"@click": f"app.press('{binding.key}')", "key": binding.key},
            )
            text.append_text(key_text)
        return text

    def render(self) -> RenderableType:
        if self._key_text is None:
            self._key_text = self.make_key_text()
        return self._key_text

    def regenerate(self) -> None:
        self._key_text = None
        # If I don't set layout=true, there seems to be some race condition
        # when both menu and footer need to be updated at similar times.
        self.refresh(layout=True)
