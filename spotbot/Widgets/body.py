from textual.widget import Widget
from textual.reactive import Reactive
from textual import events
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.style import StyleType
from typing import Union, Tuple


class Body(Widget):

    # highlight_key: Reactive[str | None] = Reactive(None)
    highlight_key = Reactive(None)
    # _key_text: Reactive[RenderableType | None] = Reactive(non)

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
            Layout(ratio=1, name="config", visible=False),
        )
        # Divide the main into two parts side-by-side
        self.layout["main"].split_row(Layout(name="left"), Layout(name="right"))

        # Create list to hold the tables
        self.servo_table = []

        # Layout of servos - positions the servo entries in the tables
        self.servo_layout = []

        # currently selected servos
        self.selection = []

        self.multi_select = False

        # Data to populate the tables
        self.mappings = {}
        self.config_mapping = {}

        # Modes: "normal" or "config"
        self.config_mode: bool = False

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
            Text("??s", justify="center"), width=6, style="none", justify="right"
        )
        table.add_column(
            Text("???", justify="center"), width=5, style="none", justify="right"
        )
        return table

    def key_press(self, key: str) -> None:
        if key not in self.selection:
            if self.multi_select is True:
                self.selection.append(key)
            else:
                self.selection = [key]
        else:
            if self.multi_select is True:
                self.selection.remove(key)
            else:
                self.selection.clear()
        self.refresh()

    def get_selection(self) -> list:
        return self.selection

    def clear_selection(self) -> None:
        self.selection.clear()

    def update_servos(self, mappings: dict) -> None:
        """Update the servo mappings and refresh the widget"""
        self.mappings = mappings
        self.refresh()

    def update_config(
        self,
        servo: str,
        desc: str,
        channel: int,
        desig: str,
        max_us: int,
        min_us: int,
        angle1_us: int,
        angle1_deg: float,
        angle2_us: float,
        angle2_deg: float,
        home_deg: float,
    ) -> None:
        self.config_mapping = {
            "servo": servo,
            "description": desc,
            "channel": str(channel),
            "designation": desig,
            "max_us": str(max_us),
            "min_us": str(min_us),
            "angle1_us": str(angle1_us),
            "angle1_deg": str(angle2_us),
            "angle2_us": str(angle1_deg),
            "angle2_deg": str(angle2_deg),
            "home_deg": str(home_deg),
        }

    def enable_config(self) -> None:
        self.config_mode = True
        self.layout["config"].visible = True
        self.refresh(layout=True)

    def disable_config(self) -> None:
        self.config_mode = False
        self.layout["config"].visible = False
        self.refresh(layout=True)

    def _create_config_panel(self) -> None:
        table = Table(show_lines=False)
        table.add_column("Servo", width=5, justify="center")
        table.add_column("Description", width=20, justify="center")
        table.add_column("Channel", width=8, justify="center")
        table.add_column("Designation", width=3, justify="center")
        table.add_column("Max ??s", width=6, justify="center")
        table.add_column("Min ??s", width=6, justify="center")
        table.add_column("Angle1 ??s", width=6, justify="center")
        table.add_column("Angle1 ???", width=6, justify="center")
        table.add_column("Angle2 ??s", width=6, justify="center")
        table.add_column("Angle2 ???", width=6, justify="center")
        table.add_column("Home ???", width=6, justify="center")
        return table

    def render(self) -> Panel:

        self.servo_table.clear()

        # Each entry in servo_layout represents a table of rows in the order to print
        for table in range(0, len(self.servo_layout)):
            # create a new table
            self.servo_table.append(self._create_servo_table())
            # for each row, fill in the values
            for row in self.servo_layout[table]:
                if row is None:
                    self.servo_table[table].add_row("", "", "", "", "")
                    continue
                (key, desc, servo, us, angle) = self.mappings[row]
                column_style = "reverse" if key in self.selection else "none"
                self.servo_table[table].add_row(
                    "[b]({})[/b]".format(key.upper()),
                    desc,
                    servo,
                    us,
                    angle,
                    style=column_style,
                )

        self.layout["left"].update(Align(self.servo_table[0], align="center"))
        self.layout["right"].update(Align(self.servo_table[1], align="center"))

        if self.config_mode is True and len(self.config_mapping) != 0:
            table = self._create_config_panel()
            table.add_row(
                self.config_mapping["servo"],
                self.config_mapping["description"],
                self.config_mapping["channel"],
                self.config_mapping["designation"],
                self.config_mapping["max_us"],
                self.config_mapping["min_us"],
                self.config_mapping["angle1_us"],
                self.config_mapping["angle1_deg"],
                self.config_mapping["angle2_us"],
                self.config_mapping["angle2_deg"],
                self.config_mapping["home_deg"],
            )
            self.layout["config"].update(Align(table, align="center"))

        return Panel(self.layout)
