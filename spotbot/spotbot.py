from textual import events
from textual.app import App
from textual.widgets import Header, Placeholder
from textual.binding import Bindings
from Widgets.footer import Footer
from Widgets.status import Status
from Widgets.menu import Menu
from Widgets.body import Body
import servo
import add_menus
import file_utils
from utils import Utils


import sys
from os.path import exists
from rich import print
import rich.traceback
import argparse


def errprint(*a):
    print(*a, file=sys.stderr)


class MyApp(App):
    """An example of a very simple Textual App"""

    status_stack = []
    menu_stack = []

    # on_load runs before the app is displayed
    async def on_load(self, event: events.Load) -> None:

        """Bind keys with the app loads (but before entering application mode)"""
        await self.bind(".", "main_menu", "Menu")
        await self.bind(
            "q",
            "confirm_y_n('[bold]Quit?[/bold] Y/N', 'quit', 'pop_status', '[Quit]')",
            "Quit",
        )

        # access convenience utilites
        self.utils = Utils(self)

        # initalize
        self.servo_mode = "angle"
        # Servo adjustment increment in µs and ∠
        self.us_increment = 1500
        self.angle_increment = 20.0

    # on mount is what is run when the applicaiton starts (after on_load)
    async def on_mount(self, event: events.Mount) -> None:
        """Create and dock the widgets."""
        self.header = Header(style="bold blue")
        self.body = Body(name="body")
        self.bodypadding = Placeholder(name="bodypadding")  # force body up

        # Status and footer will be on layer 1 and will resize with the menu,
        # Body will be on layer 0 and will not.

        # Status line
        self.status = Status(style="yellow on default")

        self.status.add_entry(
            "mode", "Mode", "∠", key_style="bold", value_style="bold blue"
        )

        self.status.add_entry(
            "angle_increment",
            "∠ Increment",
            self.utils.get_angle_increment,
            key_style="bold blue",
            value_style="bold blue",
        )

        self.status.add_entry(
            "us_increment",
            "µs Increment",
            self.utils.get_us_increment,
        )
        self.status.add_entry(
            "time",
            "Time",
            self.utils.status_clock,
        )
        self.status.layout_offset_y  # make room for footer

        # Footer
        self.footer = Footer(
            key_style="bold blue on default",
            key_hover_style="bold blue reverse",
            key_description_style="gray on default",
        )

        self.menu = Menu(
            key_style="bold blue on default",
            key_description_style="blue on default",
            menu_style="blue on default",
            refresh_callback=self.footer.regenerate,
            app=self,
        )
        self.menu.visible = False

        # Load the menus
        add_menus.add_menus(self.menu)

        # Build servo tables
        self.servo_status = {}
        self.servo_status["left"] = [
            ("a", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("b", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("c", "Front-Right-Bottom", "S0", "1500", "90.0"),
            None,
            ("d", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("e", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("f", "Front-Right-Bottom", "S0", "1500", "90.0"),
        ]

        self.servo_status["right"] = [
            ("g", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("h", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("i", "Front-Right-Bottom", "S0", "1500", "90.0"),
            None,
            ("j", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("k", "Front-Right-Bottom", "S0", "1500", "90.0"),
            ("l", "Front-Right-Bottom", "S0", "1500", "90.0"),
        ]

        # update the tables
        self.body.update(self.servo_status)

        # Bindings for servo hot-keys
        for table in self.servo_status.keys():
            for row in self.servo_status[table]:
                if row is None:
                    continue
                (key, desc, servo, us, angle) = row
                await self.bind(key, f"servo_key('{key}')", "", show=False)

        # Layout the weidgets
        await self.view.dock(self.header, edge="top")
        await self.view.dock(self.footer, size=1, edge="bottom", z=1)
        await self.view.dock(self.status, size=3, edge="bottom", z=1)
        await self.view.dock(self.menu, size=30, edge="left", name="menu", z=1)
        await self.view.dock(self.bodypadding, size=4, edge="bottom")
        await self.view.dock(self.body, edge="top")

    async def action_confirm_y_n(
        self, message: str, confirm_action: str, noconfirm_action: str, title: str = ""
    ) -> None:
        """Build Yes/No Modal Dialog and process callbacks."""

        # push current state on to the stack
        self.push_status()

        # Set new state
        self.status.message = message
        self.status.title = title
        # Tell status widget to not use the normal statuses
        self.status.regenerate_status_from_dict = False
        self.bindings = Bindings()
        await self.bind("ctrl+c", "quit", show=False)
        await self.bind("y", confirm_action, "Yes")
        await self.bind("n", noconfirm_action, "No")

        # Refresh footer
        self.footer.regenerate()

    def push_status(self) -> None:
        """Save current status and bindings"""
        self.status_stack.append(
            (self.status.message, self.bindings, self.status.title)
        )

    def pop_status(self) -> None:
        """Recover last status and bindings"""
        if len(self.status_stack) > 0:
            (
                self.status.message,
                self.bindings,
                self.status.title,
            ) = self.status_stack.pop()
            self.footer.regenerate()  # Regenerate footter
        if len(self.status_stack) == 0:
            self.status.regenerate_status_from_dict = True

    async def action_pop_status(self) -> None:
        """Back out and return to last status"""
        self.pop_status()

    async def action_main_menu(self) -> None:
        """Launch the main menu"""
        await self.menu.load_menu("main")

    async def action_tbd(self) -> None:
        """Simulate a menu-action"""
        await self.menu.pop_menu(pop_all=True)

    async def action_set_us_increment(self, increment: int) -> None:
        self.us_increment = increment
        self.status.refresh()
        await self.menu.pop_menu(pop_all=True)

    async def action_set_angle_increment(self, increment: float) -> None:
        self.angle_increment = increment
        self.status.refresh()
        await self.menu.pop_menu(pop_all=True)

    async def action_servo_key(self, key: str) -> None:
        self.body.key_press(key)

    async def action_toggle_servo_mode(self) -> None:
        if self.servo_mode == "angle":
            self.servo_mode = "us"
            self.status.update_entry("mode", "µs")
            self.status.update_entry(
                "angle_increment", key_style="none", value_style="none"
            )
            self.status.update_entry(
                "us_increment", key_style="bold blue", value_style="bold blue"
            )
        else:
            self.servo_mode = "angle"
            self.status.update_entry("mode", "∠")
            self.status.update_entry(
                "us_increment", key_style="none", value_style="none"
            )
            self.status.update_entry(
                "angle_increment", key_style="bold blue", value_style="bold blue"
            )
        self.status.refresh()
        await self.menu.pop_menu(pop_all=True)


if __name__ == "__main__":

    DEFAULT_SERIALCONFIG = "serial_config.yml"
    DEFAULT_SERVOCONFIG = "servo_config.yml"

    # smart errors
    rich.traceback.install(show_locals=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--serialconfig",
        help="Configuration file for serial access to servo controller, if "
        + "'{}' exists it will be loaded automatically ".format(DEFAULT_SERIALCONFIG)
        + "even if this parameter is not set",
        default=DEFAULT_SERIALCONFIG,
    )

    parser.add_argument(
        "--servoconfig",
        help="Servo Configuration File if "
        + "'{} exists it will be loaded automatically ".format(DEFAULT_SERVOCONFIG)
        + "even if this parameter is not set",
        default=DEFAULT_SERVOCONFIG,
    )

    parser.add_argument(
        "-t",
        "--testservo",
        help=(
            "testing - don't connect to server controller, serial settings are"
            " ignored and serial activity is stubbed out."
        ),
        action="store_true",
    )

    args = parser.parse_args()

    # if no file is specified and the default file doesn't exist, set to None which
    # will tell the loader to use the system defaults.
    if args.serialconfig == DEFAULT_SERIALCONFIG and not exists(DEFAULT_SERIALCONFIG):
        args.serialconfig = None

    serialconfig = file_utils.load_serial_configuration_file(args.serialconfig)

    # load configuration file
    config = file_utils.load_configuration_file(args.servoconfig)

    # RPI Zero W is on /dev/ttyS0
    if args.testservo is False:
        servo = servo.ServoController(**serialconfig)

    MyApp.run(log="textual.log", log_verbosity=3, title="Spotmicro Configuration")
