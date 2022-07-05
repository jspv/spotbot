from typing import Union, Tuple, List, Optional, Callable
from textual.widget import Widget
from textual.app import App
from textual.reactive import Reactive
from textual.binding import Bindings
from rich.console import RenderableType
from rich.table import Table
from rich.panel import Panel
from rich.style import StyleType


# type vector for easier reading
menuitem = Tuple[str, str, str]


class MenuItemList(object):
    """A menu, a list of menuitems with a name and a title"""

    def __init__(self, name: str, items: List[menuitem] = [], title: str = "") -> None:
        self.name = name
        self.items = items
        self.title = title


class MenuItems(object):
    """Manage a dictionary containing multiple Menu item lists"""

    def __init__(self, menus: dict = {}) -> None:
        self._menus = menus

    def add(
        self,
        arg1: Union[str, MenuItemList],
        menuitemlist: List[menuitem] = None,
        title: str = "",
    ):
        # check to see if arg1 is a string or menuitemlist
        if isinstance(arg1, str):
            if menuitemlist is None:
                raise ValueError("menuitemlist is required")
            newmenu = MenuItemList(arg1, menuitemlist, title)
        else:
            newmenu = arg1

        if newmenu.name in self._menus:
            raise ValueError("Menu {} already exists in the list of menus")
        self._menus[newmenu.name] = newmenu

    def get_menu(self, name) -> MenuItemList:
        return self._menus[name]


class Menu(Widget):
    def __init__(
        self,
        arg1: Union[list[menuitem], MenuItemList] = None,
        app: App = None,
        title: str = "",
        refresh_callback: Callable = None,
        key_style: StyleType = "bold white on dark_green",
        key_description_style: StyleType = "white on dark_green",
        menu_style: StyleType = "none",
        **kwargs,
    ) -> None:
        # Since we manage bindings, need to have a reference to the calling app
        if app is None:
            raise ValueError("App reference is required use menus")
        super().__init__(**kwargs)
        if arg1 is None:
            # create empty menu
            self._menu_items = []
            self.title = title
            self.menuname = None
        elif isinstance(arg1, MenuItemList):
            # initialize with the provided menuItemList
            self._menu_items = arg1.items
            self.title = arg1.title
            self.menuname = arg1.name
        else:
            # iniliaze with the provided data
            self._menu_items = arg1
            self.title = title
            self.menuname = None

        self.refresh_callback = refresh_callback
        # self.myapp = app
        self.key_style = key_style
        self.key_description_style = key_description_style
        self.menu_style = menu_style

    index: Reactive[int] = Reactive(0)
    menu_style: Reactive[StyleType] = Reactive("none")
    _menu_items: Reactive[List[menuitem]] = Reactive([])

    # stack for storing cascading menus and bindings
    menu_stack = []

    def _add_menu_item(
        self,
        bind_chr: Union[str, None],
        description: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        if bind_chr is not None:
            self._menu_items.append((bind_chr, description, callback))
        else:
            self._menu_items.append(None)

    def update_menu(
        self,
        arg1: Union[List[menuitem], MenuItemList],
        title: str = "",
        menuname: Union[str, None] = None,
    ) -> None:
        self.skip_rows = 0  # Reset scrolling

        if isinstance(arg1, MenuItemList):
            self._menu_items = arg1.items
            self.title = arg1.title
            self.menuname = arg1.name
            self.index = 0
        else:
            self._menu_items = arg1
            self.title = title
            self.menuname = menuname
            self.index = 0

    async def load_menu(self, menu: MenuItemList):
        """Load a show a menu, managing hotkey bindings"""

        # push current menu and bindings onto the stack
        # the pre-menu state will have menuname = None
        self.menu_stack.append(
            (self.menuname, self._menu_items, self.title, self.app.bindings)
        )

        # build and show the new menu
        self.update_menu(menu)
        await self.bind_current_menu()
        if self.refresh_callback is not None:
            self.refresh_callback()

    async def bind_current_menu(self) -> None:
        # Rebind hotkeys to new menu
        self.app.bindings = Bindings()
        await self.app.bind("ctrl+c", "quit", show=False)
        await self.app.bind("escape", "menu_escape", show=False)
        await self.app.bind("down", "menu_down", show=False)
        await self.app.bind("up", "menu_up", show=False)
        await self.app.bind("enter", "menu_enter", show=False)
        for item in self._menu_items:
            if item is None:
                continue
            (chr, description, callback) = item
            await self.app.bind(chr.lower(), callback)

    async def pop_menu(self, pop_all=False) -> None:
        """Recover last menu and bindings"""
        if pop_all is True:
            """pop all until at the bottom"""
            while self.menuname is not None:
                (
                    self.menuname,
                    self._menu_items,
                    self.title,
                    self.app.bindings,
                ) = self.menu_stack.pop()
        else:
            (
                self.menuname,
                self._menu_items,
                self.title,
                self.app.bindings,
            ) = self.menu_stack.pop()
        if self.menuname is not None:
            self.bind_current_menu()
        else:  # We're back to the main app
            self.visible = False
        if self.refresh_callback is not None:
            self.refresh_callback()

    def menu_down(self) -> None:
        while True:
            if self.index == len(self._menu_items):
                self.index = 1
            else:
                self.index += 1
            if self._menu_items[self.index - 1] is not None:
                break

    def menu_up(self) -> None:
        while True:
            if self.index == 0 or self.index == 1:
                self.index = len(self._menu_items)
            else:
                self.index -= 1
            if self._menu_items[self.index - 1] is not None:
                break

    def menu_choose(self) -> Optional[str]:
        if self.index == 0:
            return None
        # return the callback for the entry
        return self._menu_items[self.index - 1][2]

    def render(self) -> RenderableType:
        MENU_CHROME = 4  # Unusable space in the menu for titles andn padding
        menu_max_rows = self.size.height - MENU_CHROME
        subtitle = ""

        menu_table = Table.grid()
        menu_table.add_column("key", justify="left", width=5, style=self.key_style)
        menu_table.add_column(
            "action", justify="left", style=self.key_description_style
        )

        # Determine if we need to scroll
        if len(self._menu_items) > menu_max_rows:
            top = 1 if self.index == 0 else (self.skip_rows + 1)
            bottom = top + menu_max_rows - 1

            # if index would be the bottom; scroll if the bottom isn't the last row.
            if self.index == len(self._menu_items):
                self.skip_rows = self.index - menu_max_rows
            elif self.index >= bottom and bottom < len(self._menu_items):
                self.skip_rows = self.index - menu_max_rows + 1

            # if index would be the top; scroll if the top isnt the first row
            if self.index == 1:
                self.skip_rows = 0
            elif self.index <= top and top != 1:
                self.skip_rows = self.index - 2

            # Recalc top & bottom to determine subtitles
            top = 1 if self.index == 0 else (self.skip_rows + 1)
            bottom = top + menu_max_rows - 1
            if top == 1:
                subtitle = "▼  more  ▼"
            elif bottom == len(self._menu_items):
                subtitle = "▲  more  ▲"
            else:
                subtitle = "▼▲ more ▼▲"

        for count, item in enumerate(self._menu_items):
            # Account for scrolling
            if count < self.skip_rows:
                continue
            if item is None:
                menu_table.add_row("", "")
            else:
                (bind_chr, description, callback) = item
                if self.index == (count + 1):
                    menu_table.add_row(f"({bind_chr})", description, style="reverse")
                else:
                    menu_table.add_row(f"({bind_chr})", description)
        menu = Panel(
            menu_table,
            title=self.title,
            style=self.menu_style,
            padding=(1, 1),
            subtitle=subtitle,
        )
        return menu
