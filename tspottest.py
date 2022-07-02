from textual import events
from textual.app import App
from textual.widgets import Header, Placeholder
import textual.actions
import footer
import status
import menu
import body
from textual.binding import Bindings
from datetime import datetime


# Servo adjustment increment in µs
current_us_increment = 1500


def status_clock() -> str:
    return f"[r]{datetime.now().time().strftime('%X')}[/r]"


def set_us_increment(increment: int) -> None:
    """Set µs incrment"""
    global current_us_increment
    current_us_increment = increment


def get_us_increment() -> str:
    """Get current µs incrment as a str"""
    global current_us_increment
    return "{:>4}".format(str(current_us_increment))


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

    # on mount is what is run when the applicaiton starts (after on_load)
    async def on_mount(self, event: events.Mount) -> None:
        """Create and dock the widgets."""
        self.header = Header(style="bold blue")
        self.body = body.Body(name="body")
        self.bodypadding = Placeholder(name="bodypadding")  # force body up

        # Status and footer will be on layer 1 and will resize with the menu,
        # Body will be on layer 0 and will not.

        # Status line
        self.status = status.Status(style="yellow on default")
        self.status.add_entry(
            "increment", "Increment", get_us_increment, value_style="reverse"
        )
        self.status.add_entry("time", "Time", status_clock)
        self.status.layout_offset_y  # make room for footer

        # Footer
        self.footer = footer.Footer(
            key_style="bold blue on default",
            key_hover_style="bold blue reverse",
            key_description_style="gray on default",
        )

        self.menus = menu.MenuItems()
        self.menus.add(
            "main",
            [
                ("C", "Config Servo", "tbd"),
                ("I", "Change increment", "increment_menu"),
                None,
                ("L", "Load Config", "tbd"),
                ("S", "Save Config", "tbd"),
                None,
                ("D", "Set Speed", "tbd"),
                ("A", "Set Acceleration", "tbd"),
                ("E", "Sequence Menu", "tbd"),
                None,
                ("Q", "<-- Back", "menu_backout"),
            ],
            title="[bold][u]Main Menu[/u][/bold]",
        )
        self.menus.add(
            "us_increment",
            [
                ("1", "1 µs", "set_us_increment(1)"),
                ("2", "2 µs", "set_us_increment(2)"),
                ("5", "5 µs", "set_us_increment(5)"),
                ("x", "10 µs", "set_us_increment(10)"),
                ("b", "20 µs", "set_us_increment(20)"),
                ("l", "50 µs", "set_us_increment(50)"),
                ("c", "100 µs", "set_us_increment(100)"),
                ("d", "200 µs", "set_us_increment(200)"),
                None,
                ("Q", "<-- Back", "menu_backout"),
            ],
            title="[bold][u]Servo Increment (µs)[u][/bold]",
        )

        self.menu = menu.Menu(
            key_style="bold blue on default",
            key_description_style="blue on default",
            menu_style="blue on default",
        )
        self.menu.visible = False

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

    def push_menu(self) -> None:
        """Save current menu and bindings"""
        self.menu_stack.append((self.menu.menuname, self.bindings))

    async def pop_menu(self, pop_all=False) -> None:
        """Recover last menu and bindings"""
        if pop_all is True:
            """pop all until at the bottom"""
            while self.menu.menuname is not None:
                (self.menu.menuname, self.bindings) = self.menu_stack.pop()
        else:
            (self.menu.menuname, self.bindings) = self.menu_stack.pop()
        if self.menu.menuname is not None:
            await self.menu.update_menu(self.menus.get_menu(self.menu.menuname))
            await self.menu_bind(self.menus.get_menu(self.menu.menuname))
        else:  # We're back to the main app
            self.footer.regenerate()
            self.menu.visible = False

    async def menu_bind(self, menuitems: menu.MenuItemList):
        """Build new bindings and footer based on the Menu"""
        self.bindings = Bindings()
        await self.bind("ctrl+c", "quit", show=False)
        await self.bind("escape", "menu_escape", show=False)
        await self.bind("down", "menu_down", show=False)
        await self.bind("up", "menu_up", show=False)
        await self.bind("enter", "menu_enter", show=False)
        for item in menuitems.items:
            if item is None:
                continue
            (chr, description, callback) = item
            await self.bind(chr.lower(), callback)
        self.footer.regenerate()

    async def action_pop_status(self) -> None:
        """Back out and return to last status"""
        self.pop_status()

    async def action_main_menu(self) -> None:
        """Launch the main menu"""
        self.push_menu()
        await self.menu.update_menu(self.menus.get_menu("main"))
        await self.menu_bind(self.menus.get_menu("main"))
        self.menu.visible = True

    async def action_increment_menu(self) -> None:
        """Launch the increment menu"""
        if self.menu.visible is True:
            self.push_menu()
        await self.menu.update_menu(self.menus.get_menu("us_increment"))
        await self.menu_bind(self.menus.get_menu("us_increment"))
        self.menu.visible = True

    async def action_menu_backout(self) -> None:
        """Back out to previous menu"""
        await self.pop_menu()

    async def action_menu_escape(self) -> None:
        await self.pop_menu(pop_all=True)

    async def action_menu_up(self) -> None:
        self.menu.menu_up()

    async def action_menu_down(self) -> None:
        self.menu.menu_down()

    async def action_menu_enter(self) -> None:
        callback = self.menu.menu_choose()
        if callback is not None:
            # call the action directly
            target, params = textual.actions.parse(callback)
            action_target = getattr(self, f"action_{target}")
            await action_target(*params)

    async def action_tbd(self) -> None:
        """Simulate a menu-action"""
        await self.pop_menu(pop_all=True)

    async def action_set_us_increment(self, increment: int) -> None:
        set_us_increment(increment)
        await self.pop_menu(pop_all=True)


MyApp.run(log="textual.log", title="Spotmicro Configuration")
