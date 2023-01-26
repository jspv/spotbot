from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal
from textual.widgets import Footer, Header, Static, Button, Placeholder
from .Widgets.body import Body
from .Widgets.status import Status
from .Widgets.dialog import Dialog
from .Widgets.menu import Menu
from textual.screen import Screen
from textual.binding import Binding, Bindings
from textual import log
from textual.reactive import var
from rich.text import Text

from . import file_utils
from . import GPIO as gpio
from . import add_menus
from .utils import Utils

import sys

# atexit allows for registering exit handlers, allows us to ensure GPIO conneciton
# gets closed on exit.
import atexit

import rich
import argparse
import importlib


class Spotbot(App):

    CSS_PATH = "spotbot.css"

    """Bind keys when the app loads (but before entering application mode)"""

    BINDINGS = [
        Binding(
            key="full_stop", action="main_menu", description="Menu", key_display="."
        ),
        (
            "q",
            "confirm_y_n('[bold]Quit?[/bold] Y/N', 'quit', 'close_dialog', '[Quit]')",
            "Quit",
        ),
        (
            "backslash",
            (
                "confirm_y_n('[b]Enable Servos?[/b] Y/N', 'toggle_relay', "
                "'close_dialog', '[Enable Servos]')"
            ),
            "Enable Servos",
        ),
    ]

    status_stack = []
    menu_stack = []

    def __init__(self, *args, **kwargs) -> None:
        log(sys.argv)
        self.parse_args_and_initialize()

        # access convenience utilites
        self.utils = Utils(self)

        # initalize defaults
        self.servo_mode = "angle"
        # Servo adjustment increment in µs and ∠
        self.us_increment = 100
        self.angle_increment = 20.0

        # Dict to store servo data
        self.servo_data = {}

        super().__init__(*args, **kwargs)

    def parse_args_and_initialize(self):
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
            help="Override pose configuration file specified in {}".format(
                DEFAULT_CONFIG
            ),
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

        # args = parser.parse_args()
        args, unknown = parser.parse_known_args()
        print(f"Received known args: {args}")
        print(f"Received unknown args: {unknown}")

        if args.verbose is True:  # smart errors
            rich.traceback.install(show_locals=True)

        configfile = file_utils.ConfigFile(args.config)

        if args.servoconfig is None:
            args.servoconfig = configfile.config["servo_config"]

        if args.poseconfig is None:
            args.poseconfig = configfile.config["pose_config"]

        # import the correct servo library based on the servoboard
        servolib = importlib.import_module(
            ".{}".format(configfile.config["servoboard"]), package="spotbot.Servo"
        )

        # If there is a relay to power the servos, configure it with GPIO
        if "relay_settings" in configfile.config:
            self.relay = gpio.Relay(
                configfile.config["relay_settings"]["gpio"],
                configfile.config["relay_settings"]["active_high"],
            )
            atexit.register(self.relay.close)
        else:
            self.relay = None

        # Connect to the servo board and get a controller object
        self.servo_ctl = (
            servolib.ServoController(**configfile.config["serial_settings"])
            if args.testservo is False
            else None
        )

        # load servo configuration file
        self.servo_configfile = file_utils.ServoConfiFile(
            args.servoconfig, self.servo_ctl
        )
        self.servos = self.servo_configfile.load()

    def run(self, *args, **kwargs):
        try:
            super().run(*args, **kwargs)
        # naked exception to catch any failure and ensure we shut down the relay
        except:  # noqa E722
            if self.relay is not None:
                self.relay.close()
            raise

    def loadargs(self, **kwargs) -> None:
        """Transform kwargs into self.arg values"""
        for (k, v) in kwargs.items():
            setattr(self, k, v)

    def push_status(self) -> None:
        """Save current status and bindings"""
        # hack - changing bindings not currently supported in Textual
        self.status_stack.append((self._bindings))

    def pop_status(self) -> None:
        """Restore last status and bindings"""
        # hack - changing bindings not currently supported in Textual
        if len(self.status_stack) > 0:
            (self._bindings) = self.status_stack.pop()

    def compose(self) -> ComposeResult:
        # describe the display table layout
        servo_layout = [
            ["A", "B", "C", None, "D", "E", "F"],
            ["G", "H", "I", None, "J", "K", "L"],
        ]
        self.dialog = Dialog(id="modal_dialog")
        self.footer = Footer()
        self.body = Body(servo_layout, id="p1")
        self.status = Status(id="status")
        self.menu = Menu(id="menu")

        yield Header()
        yield Container(
            Horizontal(self.menu, self.body, Placeholder(id="p2")),
            self.status,
            id="mainscreen",
        )
        # yield ConfigArea()
        yield self.footer

        # Modal Dialog
        yield self.dialog

    def action_confirm_y_n(
        self, message: str, confirm_action: str, noconfirm_action: str, title: str = ""
    ) -> None:
        """Build Yes/No Modal Dialog and process callbacks."""
        dialog = self.query_one("#modal_dialog", Dialog)
        dialog.confirm_action = confirm_action
        dialog.noconfirm_action = noconfirm_action
        dialog.set_message(message)
        dialog.show_dialog()

    def on_mount(self) -> None:
        # Set the text of the dialog message and buttons
        self.status.add_entry(
            key="servo",
            keymsg="Servo Relay",
            value=lambda: "[r]On[/r] :warning-emoji: "
            if self.relay.is_active()
            else "Off",
        )
        self.status.add_entry(
            key="mode",
            keymsg="Mode",
            value=lambda: "∠" if self.servo_mode == "angle" else "µs",
        )

        self.status.add_entry(
            key="angle_increment",
            keymsg="∠ Increment",
            value=self.utils.get_angle_increment,
        )

        self.status.add_entry(
            key="us_increment",
            keymsg="µs Increment",
            value=self.utils.get_us_increment,
        )

        self.status.add_entry(
            key="multi",
            keymsg="Multiselect",
            value=lambda: "[r]On[/r] " if self.body.multi_select else "Off",
        )
        # force a status widget udpdate
        self.status.update_status()

        # load the servo tables with the current servo data
        for servoletter in [chr(i) for i in range(ord("A"), ord("R"))]:
            if servoletter in self.servos:
                self.refresh_servo_data(servoletter)

        # load the menus
        add_menus.add_menus(self.menu)

        # set focus to the body widget
        self.body.focus()

    def refresh_servo_data(self, servoletter: str) -> None:
        """Update the servo data table for a specific servo"""
        servo = self.servos[servoletter]
        self.servo_data[servoletter] = (
            servoletter,
            servo.description,
            servo.designation,
            str(servo.position_us),
            str(servo.home_deg),
        )
        self.body.update_servos(self.servo_data)

    ###########
    # Actions #
    ###########

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

        self.status.update_status()
        await self.menu.pop_menu(pop_all=True)

        # Refresh bindings if needed
        if len(self.body.selection) != 0:
            symbol = "∠" if self.servo_mode == "angle" else "µs"
            self.body.bind("up", "servo_increment", f"Increment {symbol}")
            self.body.bind("down", "servo_decrement", f"Decrement {symbol}")
            # self.footer.regenerate()

    def action_servo_increment(self) -> None:
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

    def action_servo_decrement(self) -> None:
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

    def action_servo_off(self) -> None:
        for servoletter in self.body.selection:
            self.servos[servoletter].stop()
            self.refresh_servo_data(servoletter)

    def _action_toggle_relay(self) -> None:
        self.relay.toggle()
        # if relay is currently on, then we just came out of modal dialog, close it.
        if self.relay.is_active() is True:
            self.dialog.action_close_dialog()
            self.app.bind("backslash", "toggle_relay", description="Disable Servos")
        else:
            self.app.bind(
                "backslash",
                (
                    "confirm_y_n('[b]Enable Servos?[/b] Y/N', 'toggle_relay', "
                    "'close_dialog', '[Enable Servos]')"
                ),
                description="Enable Servos",
            )
            self.footer._key_text = None
            self.footer.refresh()
        # update the status bar
        self.status.update_status()

    def _action_main_menu(self) -> None:
        """Launch the main menu"""
        self.menu.load_menu("main")

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

    async def on_body_status_update(self, message: Body.StatusUpdate) -> None:
        """Let Status Widget know to process an update"""
        self.status.update_status()

    async def on_dialog_focus_message(self, message: Dialog.FocusMessage) -> None:
        """Let Body widget know the current focus state"""
        if message.focustaken is True:
            self.body.disabled = True
        else:
            self.body.disabled = False

    async def on_menu_focus_message(self, message: Menu.FocusMessage) -> None:
        await self.on_dialog_focus_message(message)
        self.footer._key_text = None
        self.footer.refresh()


def clocktime() -> str:
    from datetime import datetime

    return datetime.now().strftime("%H:%M:%S")


def main() -> None:
    Spotbot().run()


if __name__ == "__main__":
    main()
