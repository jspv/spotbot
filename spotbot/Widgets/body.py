from textual.app import ComposeResult, RenderResult
from textual.widgets import Static
from textual.binding import Bindings
from textual.message import Message, MessageTarget
from textual import log
from textual import events
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich.panel import Panel
from textual.reactive import Reactive
import rich.repr


class Body(Static):

    highlight_key: Reactive[str | None] = Reactive(None)

    COMPONENT_CLASSES = {
        "body--highlight-key",
        "body--row",
        "body--header",
    }

    # bindings are also managed directly and not through the BINDINGS variable
    # only leaving this here since its where people will look for BINDINGS
    BINDINGS = [
        (
            "equals_sign",
            "confirm_y_n('[b]Set servos to home position[/b] Y/N', "
            "'set_servos_home','close_dialog', '[Home]')",
            "Home Servos",
        ),
        ("m", "toggle_multi_select", "Multi-Select"),
    ]

    # This is the main screen, enable focus
    can_focus = True

    class StatusUpdate(Message):
        """Message to inform status widget an update is pending"""

        def __init__(self, sender: MessageTarget) -> None:
            super().__init__(sender)

    def __init__(self, servo_layout, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a left/right layout using Rich
        self.layout = Layout()
        self.layout.split_row(Layout(name="left"), Layout(name="right"))

        # Layout of servos - describes the positoins of the servo entries in the tables
        self.servo_layout = servo_layout

        # Is multi-select on
        self.multi_select = False

        # Servo Table Data
        self.servo_tables = []

        # Data to populate the tables
        self.mappings = {}

        # currently selected servos
        self._selection = []

        # the output text, if set to None, will generate new text.
        self._servo_text: Text | None = None

        # Create BINDINGS for servo hot-keys
        for table in self.servo_layout:
            for row in table:
                if row is None:
                    continue
                self.bind(row, f"servo_key('{row}')", "", show=False)
                self.bind(row.lower(), f"servo_key('{row}')", "", show=False)

    async def watch_highlight_key(self, value) -> None:
        """If highlight key changes we need to regenerate the text."""
        self._servo_text = None

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        """Store any key we are moving over."""
        self.highlight_key = event.style.meta.get("key")

    async def on_leave(self, event: events.Leave) -> None:
        """Clear any highlight when the mouse leave the widget"""
        self.highlight_key = None

    # Below is in _footer.py, not sure if I need them yet.
    # def on_mount(self) -> None:
    #     watch(self.screen, "focused", self._focus_changed)

    # def _focus_changed(self, focused: Widget | None) -> None:
    #     self._servo_text = None
    #     self.refresh()

    def __rich_repr__(self) -> rich.repr.Result:
        yield from super().__rich_repr__()

    def _create_servo_table(self) -> Table:
        """Create and format a Rich Table to hold the the servo data"""

        row_style = [self.get_component_rich_style("body--row")]
        header_style = self.get_component_rich_style("body--header")

        table = Table(show_lines=False, header_style=header_style, row_styles=row_style)
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
        if key not in self._selection:
            if self.multi_select is True:
                self._selection.append(key)
            else:
                self._selection = [key]
        else:
            if self.multi_select is True:
                self._selection.remove(key)
            else:
                self._selection.clear()
        self._servo_text = None
        self.refresh()

    def get_selection(self) -> list:
        return self._selection

    async def clear_selection(self) -> None:
        self._selection.clear()

    def update_servos(self, mappings: dict) -> None:
        """Update the servo mappings and refresh the widget"""
        self.mappings = mappings
        # self.refresh()

    def make_servo_text(self) -> Text:
        self.servo_tables.clear()
        base_style = self.rich_style
        highlight_key_style = self.get_component_rich_style("body--highlight-key")

        # Each entry in servo_layout represents a table of rows in the order to print
        for table in range(len(self.servo_layout)):
            # create a new table
            self.servo_tables.append(self._create_servo_table())
            # for each row, fill in the values
            for row in self.servo_layout[table]:
                if row is None:
                    self.servo_tables[table].add_row("", "", "", "", "")
                    continue
                (key, desc, servo, us, angle) = self.mappings[row]
                column_style = "reverse" if key in self._selection else "none"
                hovered = self.highlight_key == key
                # hovered = False
                key_text = Text.assemble(
                    (
                        f"({key.upper()})",
                        highlight_key_style if hovered else base_style,
                    ),
                    # add metadata which says what to do when clicked, the 'key'
                    # metadata is for hovering.
                    meta={"@click": f"servo_key('{key}')", "key": key},
                )
                self.servo_tables[table].add_row(
                    key_text,
                    desc,
                    servo,
                    us,
                    angle,
                    style=column_style,
                )

        self.layout["left"].update(Align(self.servo_tables[0], align="center"))
        self.layout["right"].update(Align(self.servo_tables[1], align="center"))

        return Panel(self.layout)

    def render(self) -> RenderResult:

        if self._servo_text is None:
            self._servo_text = self.make_servo_text()
        return self._servo_text

    def post_render(self, renderable):
        return renderable

    ###########
    # Actions #
    ###########

    def _action_servo_key(self, key: str) -> None:
        """Process servo hotkey

        Parameters
        ----------
        key : str
            Hotkey pressed,
        """
        # Ingore servo keys when menus are active
        # if self.menu.visible is True:
        #     return

        # Get the footer to force updates
        # hack - changing bindings not currently supported in textual

        footer = self.app.query_one("Footer")

        self.key_press(key)
        if len(self._selection) == 0:
            self.unbind("up")
            self.unbind("down")
            self.unbind("0")
            # hack to refresh footer, changing bindings not currently in Textual
            footer._key_text = None
            footer.refresh()
        else:
            symbol = "∠" if self.app.servo_mode == "angle" else "µs"
            self.bind("up", "servo_increment", description=f"Increment {symbol}")
            self.bind("down", "servo_decrement", description=f"Decrement {symbol}")
            self.bind("0", "servo_off", description="Servo Off")
            # hack to refresh footer, changing bindings not currently in Textual
            footer._key_text = None
            footer.refresh()

    async def _action_toggle_multi_select(self) -> None:
        self.multi_select = not self.multi_select
        # Let the app know to update the Status Widget
        await self.emit(self.StatusUpdate(self))

    def bind(self, *args, **kwargs) -> None:
        """Create bind method - hack - not currently supported in Textual"""
        self._bindings.bind(*args, **kwargs)

    def unbind(self, key: str) -> None:
        """Create unbind method - hack - not currently supported in Textual
        Parameters
        ----------
        key : str
            key to unbind
        """
        # Raise exception if key doesn't exist
        self._bindings.get_key(key)
        del self._bindings.keys[key]
