from os import truncate
from textual.widget import Widget
from textual.reactive import Reactive
from textual.binding import Bindings
from textual import events
from rich.panel import Panel
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.style import StyleType
import rich.repr
import sys
from textual.views import GridView
from textual_inputs import TextInput
from .. import Servos
from typing import Union, Tuple


@rich.repr.auto
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
        self._key_text: Text | None = None

        self.layout = Layout()

        # Create the screen layout
        self.layout.split(
            Layout(ratio=1, name="main"),
        )
        # Divide the main into two parts side-by-side
        self.layout["main"].split_row(Layout(name="left"), Layout(name="right"))

        # Create list to hold the tables
        self.servo_table = []

        # Layout of servos - positions the servo entries in the tables
        self.servo_layout = []

        self.multi_select = False

        # Data to populate the tables
        self.mappings = {}
        self.config_mapping = {}

        # Allow the application to access actions in this namespace
        self.app._action_targets.add("body")

    # currently selected servos
    selection: Reactive[list] = []

    highlight_key: Reactive[str | None] = Reactive(None)

    async def watch_highlight_key(self, value) -> None:
        """If highlight key changes we need to regenerate the text."""
        self._key_text = None

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
            Text("µs", justify="center"), width=6, style="none", justify="right"
        )
        table.add_column(
            Text("∠", justify="center"), width=5, style="none", justify="right"
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

    async def clear_selection(self) -> None:
        self.selection.clear()

    def update_servos(self, mappings: dict) -> None:
        """Update the servo mappings and refresh the widget"""
        self.mappings = mappings
        self.refresh()

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
                hovered = self.highlight_key == key
                key_text = Text.assemble(
                    (
                        f"({key.upper()})",
                        "bold green reverse" if hovered else "bold yellow on default",
                    ),
                    # add metadata which says what to do when clicked, the 'key'
                    # metadata is for hovering.
                    meta={"@click": f"app.servo_key('{key}')", "key": key},
                )
                self.servo_table[table].add_row(
                    key_text,
                    desc,
                    servo,
                    us,
                    angle,
                    style=column_style,
                )

        self.layout["left"].update(Align(self.servo_table[0], align="center"))
        self.layout["right"].update(Align(self.servo_table[1], align="center"))

        return Panel(self.layout)


class ConfigArea(GridView):

    current_tab_index: Reactive[int] = Reactive(-1)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Modes: "normal" or "config"
        self.config_mode: bool = False
        self.tab_index = [
            "servo",
            "description",
            "designation",
            "channel",
            "max_us",
            "min_us",
            "angle1_us",
            "angle1_deg",
            "angle2_us",
            "angle2_deg",
            "home_deg",
        ]
        # list of config form entries, each entry is a dict of (desc, widget, focusable)
        self.config_itemlist = []

        # Allow the application to access actions in this namespace
        self.app._action_targets.add("config")

    async def on_mount(self) -> None:
        # Create config widgets - the NULL values will be replace when
        # update_config_mappings is called

        self._add_config_entry("servo", "servo", "")
        self._add_config_entry("description", "description", "")
        self._add_config_entry("designation", "designation", "")
        self._add_config_entry("channel", "channel", "")
        self._add_config_entry("max_us", "maximum µs", "")
        self._add_config_entry("min_us", "minumum µs", "")
        self._add_config_entry("angle1_us", "Angle 1 µs", "")
        self._add_config_entry("angle1_deg", "Angle 1 ∠", "")
        self._add_config_entry("angle2_us", "Angle 2 µs", "")
        self._add_config_entry("angle2_deg", "Angle 2 ∠", "")
        self._add_config_entry("home_deg", "Home Position ∠", "")

        # layout the widgets in a grid
        self.grid.set_align("center", "center")
        self.grid.set_gap(1, 0)
        self.grid.add_column("column", size=30)
        self.grid.add_row("row", repeat=11, size=3)
        for entry in self.config_itemlist:
            self.grid.add_widget(entry["widget"])

    def _add_config_entry(
        self, shortname: Text, description: Text, value, focusable=True
    ) -> None:
        entry = {}
        entry["shortname"] = shortname
        entry["desc"] = description
        entry["widget"] = TextInput(name=shortname, value=value, title=description)
        entry["focusable"] = focusable
        self.config_itemlist.append(entry)

    def _get_config_widget(self, shortname) -> None:
        """return widget given the shortname"""
        for item in self.config_itemlist:
            if item["shortname"] == shortname:
                return item["widget"]

    async def update_config_mapping(self, servo: Servos.Servo) -> None:
        """Load the servo data into the config widgets"""
        self.config_mapping = {
            "servo": servo.lettermap,
            "description": servo.description,
            "channel": str(servo.channel),
            "designation": servo.designation,
            "max_us": str(servo.max_us),
            "min_us": str(servo.min_us),
            "angle1_us": str(servo.angle1_us),
            "angle1_deg": str(servo.angle1_deg),
            "angle2_us": str(servo.angle2_us),
            "angle2_deg": str(servo.angle2_deg),
            "home_deg": str(servo.home_deg),
        }
        # Update the values in the config widgets
        for name, value in self.config_mapping.items():
            widget = self._get_config_widget(name)
            widget.value = value
            widget.refresh()

    async def clear_config_mappings(self) -> None:
        """Clear the servo data from the config widgets"""
        self.config_mapping = {
            "servo": "",
            "description": "",
            "channel": "",
            "designation": "",
            "max_us": "",
            "min_us": "",
            "angle1_us": "",
            "angle1_deg": "",
            "angle2_us": "",
            "angle2_deg": "",
            "home_deg": "",
        }
        # Update the values in the config widgets
        for name, value in self.config_mapping.items():
            widget = self._get_config_widget(name)
            widget.value = value

    async def enable_config(self) -> None:
        """Turn on the config widget area"""
        self.config_mode = True
        self.config_edit_mode = False
        if self.visible is False:
            await self.app.view.action_toggle(self.name)

        # set all the widgets to be non-focusable until edit is enabled
        for item in self.config_itemlist:
            item["widget"].can_focus = False

    async def disable_config(self) -> None:
        """Turn off the config widget area"""
        self.config_mode = False
        self.config_edit_mode = False
        if self.visible is True:
            await self.app.view.action_toggle(self.name)

    async def enable_config_edit(self) -> None:
        if self.config_mode is False:
            raise AttributeError("cannot enable config_edit when not in config mode")
        self.config_edit_mode = True
        self.app.bindings = Bindings()
        await self.app.bind("ctrl+c", "quit", show=False)
        if self.app.relay is not None:
            await self.app.bind(
                "\\",
                (
                    "confirm_y_n('[b]Enable Servos?[/b] Y/N', 'toggle_relay', "
                    "'pop_status', '[Enable Servos]')"
                ),
                "Enable Servos",
            )
        await self.app.bind(
            "escape",
            "toggle_config_edit",
            "Cancel Config Edit",
        )
        # Bind the editing keys
        await self.app.bind("enter", "config.submit", "Submit")
        # await self.app.bind("escape", "body.reset_focus", show=False)
        await self.app.bind("ctrl+i", "config.next_tab_index", show=False)
        await self.app.bind("shift+tab", "config.previous_tab_index", show=False)

        # set all the focusable widgets to be focusable
        for item in self.config_itemlist:
            if item["focusable"] is True:
                item["widget"].can_focus = True

        # set focus to the first tiem
        await self.config_itemlist[0]["widget"].focus()

    async def disable_config_edit(self) -> None:
        self.config_edit_mode = False
        await self.focus()
        # set all the focusable widgets to be non-focusable
        for item in self.config_itemlist:
            if item["focusable"] is True:
                item["widget"].can_focus = False

    async def action_next_tab_index(self) -> None:
        """Changes the focus to the next form field"""
        if self.current_tab_index < len(self.tab_index) - 1:
            self.current_tab_index += 1
        else:
            self.current_tab_index = 0
        await self._get_config_widget(self.tab_index[self.current_tab_index]).focus()

    async def action_previous_tab_index(self) -> None:
        """Changes the focus to the previous form field"""
        if self.current_tab_index > 0:
            self.current_tab_index -= 1
        else:
            self.current_tab_index = len(self.tab_index) - 1
        await self._get_config_widget(self.tab_index[self.current_tab_index]).focus()
