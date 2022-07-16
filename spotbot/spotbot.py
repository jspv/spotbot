from textual import events
from .App import App
from textual.widgets import Header, Placeholder
from textual.binding import Bindings
from .Widgets.footer import Footer
from .Widgets.status import Status
from .Widgets.menu import Menu
from .Widgets.body import Body
from rich.text import Text

from . import add_menus
from . import file_utils
from .utils import Utils

from . import GPIO as gpio
import atexit

import importlib
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
        await self.bind(
            "=",
            (
                "confirm_y_n('[b]Set servos to home position[/b] Y/N', "
                "'set_servos_home','pop_status', '[Home]')"
            ),
            "Home Servos",
        )

        if self.relay is not None:
            await self.bind(
                "\\",
                (
                    "confirm_y_n('[b]Enable Servos?[/b] Y/N', 'toggle_relay', "
                    "'pop_status', '[Enable Servos]')"
                ),
                "Enable Servos",
            )

        # access convenience utilites
        self.utils = Utils(self)

        # initalize defaults
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

        if self.relay is not None:
            self.status.add_entry(
                "relay_status", "Servo Power", self.utils.is_relay_on_off
            )

        self.status.add_entry(
            "time",
            "Time",
            self.utils.status_clock,
        )
        self.status.layout_offset_y  # make room for footer

        #
        # Footer
        #
        self.footer = Footer(
            key_style="bold blue on default",
            key_hover_style="bold blue reverse",
            key_description_style="gray on default",
        )

        #
        # Menu
        #
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

        # # Build servo data
        self.servo_data = {}

        #
        # Main Body
        #

        # load the current servo data
        for servoletter in [chr(i) for i in range(ord("A"), ord("R"))]:
            if servoletter in self.servos:
                self.refresh_servo_data(servoletter)

        # describe the display table layout
        self.body.servo_layout = [
            ["A", "B", "C", None, "D", "E", "F"],
            ["G", "H", "I", None, "J", "K", "L"],
        ]

        # send the data to the Widget
        self.body.update(self.servo_data)

        # Bindings for servo hot-keys
        for table in self.body.servo_layout:
            for row in table:
                if row is None:
                    continue
                await self.bind(row, f"servo_key('{row}')", "", show=False)
                await self.bind(row.lower(), f"servo_key('{row}')", "", show=False)

        # Layout the widgets
        await self.view.dock(self.header, edge="top")
        await self.view.dock(self.footer, size=1, edge="bottom", z=1)
        await self.view.dock(self.status, size=3, edge="bottom", z=1)
        await self.view.dock(self.menu, size=30, edge="left", name="menu", z=1)
        await self.view.dock(self.bodypadding, size=4, edge="bottom")
        await self.view.dock(self.body, edge="top")

    #
    # Status bar push and pop
    #
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

    def refresh_servo_data(self, servoletter: str) -> None:
        servo = self.servos[servoletter]
        self.servo_data[servoletter] = (
            servoletter,
            servo.description,
            servo.designation,
            str(servo.position_us),
            str(servo.home_angle),
        )
        self.body.update(self.servo_data)

    #
    # Actions
    #
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
        """Process servo hotkey

        Parameters
        ----------
        key : str
            Hotkey pressed,
        """
        self.body.key_press(key)
        if len(self.body.selection) == 0:
            self.unbind("up")
            self.unbind("down")
            self.unbind("0")
            self.footer.regenerate()
        else:
            symbol = "∠" if self.servo_mode == "angle" else "µs"
            await self.bind("up", "servo_increment", f"Increment {symbol}")
            await self.bind("down", "servo_decrement", f"Decrement {symbol}")
            await self.bind("0", "servo_off", "Servo Off")
            self.footer.regenerate()

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

        # Refresh bindings if needed
        if len(self.body.selection) != 0:
            symbol = "∠" if self.servo_mode == "angle" else "µs"
            await self.bind("up", "servo_increment", f"Increment {symbol}")
            await self.bind("down", "servo_decrement", f"Decrement {symbol}")
            self.footer.regenerate()

    async def action_servo_increment(self) -> None:
        for servoletter in self.body.selection:
            if self.servo_mode == "us":
                self.servos[servoletter].position_us = (
                    self.servos[servoletter].position_us + self.us_increment
                )
            else:
                self.servos[servoletter].position_angle = (
                    self.servos[servoletter].position_angle + self.angle_increment
                )
            self.refresh_servo_data(servoletter)

    async def action_servo_decrement(self) -> None:
        for servoletter in self.body.selection:
            if self.servo_mode == "us":
                self.servos[servoletter].position_us = (
                    self.servos[servoletter].position_us - self.us_increment
                )
            else:
                self.servos[servoletter].position_angle = (
                    self.servos[servoletter].position_angle - self.angle_increment
                )
            self.refresh_servo_data(servoletter)

    async def action_servo_off(self) -> None:
        for servoletter in self.body.selection:
            self.servos[servoletter].stop()
            self.refresh_servo_data(servoletter)

    async def action_toggle_relay(self) -> None:
        self.relay.toggle()
        # if relay is currently on, then we just came out of modal dialog
        if self.relay.is_active() is True:
            self.pop_status()
            await self.bind("\\", "toggle_relay", "Disable Servos")
        else:
            await self.bind(
                "\\",
                (
                    "confirm_y_n('[b]Enable Servos?[/b] Y/N', 'toggle_relay', "
                    "'pop_status', '[Enable Servos]')"
                ),
                "Enable Servos",
            )
            self.footer.regenerate()

    async def action_save_servo_config(self) -> None:
        self.servo_configfile.save()
        await self.menu.pop_menu(pop_all=True)


def main():

    DEFAULT_CONFIG = "config.yml"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="Configuration file for serial access to servo controller, if "
        + "'{}' exists it will be loaded automatically ".format(DEFAULT_CONFIG)
        + "unless this parameter specifies a different config file",
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--servoconfig",
        help="Override servo config file specified in {}".format(DEFAULT_CONFIG),
    )

    parser.add_argument(
        "--poseconfig",
        help="Override pose configuration file specified in {}".format(DEFAULT_CONFIG),
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

    parser.add_argument(
        "-v", "--verbose", help="Increase verbosity", action="store_true"
    )

    args = parser.parse_args()

    if args.verbose is True:  # smart errors
        rich.traceback.install(show_locals=True)

    configfile = file_utils.ConfigFile(args.config)

    if args.servoconfig is None:
        args.servoconfig = configfile.config["servo_config"]

    if args.poseconfig is None:
        args.poseconfig = configfile.config["pose_config"]

    servolib = importlib.import_module(
        ".Servo.{}".format(configfile.config["servoboard"]), package="spotbot"
    )

    if "relay_settings" in configfile.config:
        relay = gpio.Relay(
            configfile.config["relay_settings"]["gpio"],
            configfile.config["relay_settings"]["active_high"],
        )
        atexit.register(relay.close)
    else:
        relay = None

    # Connect to the servo board and get a controller object
    servo_ctl = (
        servolib.ServoController(**configfile.config["serial_settings"])
        if args.testservo is False
        else None
    )

    # load servo configuration file
    servo_configfile = file_utils.ServoConfiFile(args.servoconfig, servo_ctl)
    servos = servo_configfile.load()

    # load pose configuraiton file
    # pose_config=

    try:
        MyApp.run(
            log="textual.log",
            log_verbosity=3,
            title="Spotmicro Configuration",
            servo_ctl=servo_ctl,
            servos=servos,
            servo_configfile=servo_configfile,
            relay=relay,
        )
    except:
        if relay is not None:
            relay.close
        raise


if __name__ == "__main__":
    main()
