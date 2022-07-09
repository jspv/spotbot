from textual.widget import Widget
from textual.reactive import Reactive
from textual import events
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.style import StyleType
from typing import Union


class Body(Widget):
    def __init__(
        self,
        *args,
        style: StyleType = "yellow on default",
        title: Union[Text, str] = "",
        title_align: str = "center",
        mappings: dict = {},
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.layout = Layout()

        # Divide the screen into four parts
        self.layout.split(
            # Layout(name="header", size=1),
            Layout(ratio=1, name="main"),
        )

        # Divide the main into two parts side-by-side
        self.layout["main"].split_row(Layout(name="left"), Layout(name="right"))

        # Create dict to hold the tables
        self.servo_table = {}

    # Create the initial mappings
    mappings: Reactive[dict] = Reactive({})

    # Store selected servo
    selection: Reactive[str] = Reactive("")

    # highlight_key: Reactive[str | None] = Reactive(None)
    highlight_key = Reactive(None)
    # _key_text: Reactive[RenderableType | None] = Reactive(non)

    async def watch_highlight_key(self, value) -> None:
        """If highlight key changes we need to regenerate the text."""
        pass

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        """Store any key we are moving over."""
        self.highlight_key = event.style.meta.get("key")

    async def on_leave(self, event: events.Leave) -> None:
        """Clear any highlight when the mouse leave the widget"""
        self.highlight_key = None

    def _create_servo_table(self) -> Table:
        """Create and format servo table"""

        table = Table(show_lines=False)
        table.add_column("key", width=3, style="none", justify="center")
        table.add_column(
            Text("desc", justify="center"),
            width=20,
            style="none",
            justify="left",
        )
        table.add_column(Text("S#", justify="center"), width=3, justify="right")
        table.add_column(
            Text("µs", justify="center"), width=4, style="none", justify="right"
        )
        table.add_column(
            Text("∠", justify="center"), width=5, style="none", justify="right"
        )
        return table

    def key_press(self, key: str) -> None:
        if key != self.selection:
            self.selection = key
        else:
            self.selection = ""

    def get_selection(self) -> str:
        return self.selection

    def clear_selection(self) -> None:
        self.selection = ""

    def update(self, mappings: dict) -> None:
        """Update the servo mappings and refresh the widget"""
        self.mappings = mappings

    def render(self) -> Panel:

        self.servo_table["left"] = self._create_servo_table()
        self.servo_table["right"] = self._create_servo_table()

        for table in ["left", "right"]:
            for row in self.mappings[table]:
                if row is None:
                    self.servo_table[table].add_row("", "", "", "", "")
                    continue
                (key, desc, servo, us, angle) = row
                column_style = "reverse" if self.selection == key else "none"
                self.servo_table[table].add_row(
                    "[b]({})[/b]".format(key.upper()),
                    desc,
                    servo,
                    us,
                    angle,
                    style=column_style,
                )

        self.layout["left"].update(Align(self.servo_table["left"], align="center"))
        self.layout["right"].update(Align(self.servo_table["right"], align="center"))

        return Panel(self.layout)
