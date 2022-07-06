from typing import Union, Tuple, List, Optional, Callable
from textual.widget import Widget
from textual.app import App
from textual.reactive import Reactive
from textual.binding import Bindings
import textual.actions
from rich.console import RenderableType
from rich.table import Table
from rich.panel import Panel
from rich.style import StyleType
from rich.text import Text


# type vector for easier reading (bindchar, description, callback)
menuitem = Tuple[Union[str, Text], Union[str, Text], str]


class MenuItemList(object):
    """A menu - which is a list of menuitems with a name and a title"""

    def __init__(self, name: str, items: List[menuitem] = [], title: str = "") -> None:
        self.name = name
        self.items = items
        self.title = Text.from_markup(title)

        # Ensure that the description fields are Text type, this allows for proper
        # length calculation with len()
        for index, item in enumerate(items):
            if item is not None and isinstance(item[1], Text) is False:
                items[index] = (item[0], Text.from_markup(item[1]), item[2])


class MenuBook(object):
    """Manage a dictionary containing multiple Menu item lists"""

    def __init__(self) -> None:
        self._menus = {}

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

        self._menus[newmenu.name] = newmenu

    def get_menu(self, name) -> MenuItemList:
        return self._menus[name]


class Menu(Widget):

    # _menu_items: Reactive[List[menuitem]] = Reactive([])
    # Not sure why, but reactives need to be class variables and they work
    # fine even when shadowed
    index: Reactive[int] = Reactive(0)
    menu_style: Reactive[StyleType] = Reactive("none")
    _menu_items: List[menuitem] = []

    def __init__(
        self,
        arg1: Union[list[menuitem], MenuItemList] = None,
        app: App = None,
        title: str = "",
        refresh_callback: Callable = None,
        key_style: StyleType = "bold white on dark_green",
        key_description_style: StyleType = "white on dark_green",
        menu_style: StyleType = "none",
        max_size: int = 50,
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
        self.key_style = key_style
        self.key_description_style = key_description_style
        self.menu_style = menu_style
        self.max_size = max_size

        # keep an internal menubook
        self.menubook = MenuBook()

        # stack for storing cascading menus and bindings
        self.menu_stack = []

        # Allow the applicaiton to access actions in this namespace
        self.app._action_targets.add("menu")

    def add_menu(
        self,
        menu: Union[str, MenuItemList],
        menulist: List[menuitem] = [],
        title: str = "",
    ) -> None:
        """Add a menu to the menubook which then can be loaded by name

        Parameters
        ----------
        menu : Union[List[menuitem], MenuItemList]
            either a MenuItemList or a name of new menu items, if the latter, the
            menulist and and title should be provided
        menulist : List[menuitem], by default []
            list of menuitems, if needed, by default ""
        title : str, optional
            menu title, if needed, by default ""
        """
        # convert menu to MenuItemList if needed
        if isinstance(menu, MenuItemList) is False:
            menu = MenuItemList(menu, menulist, title)

        # Add the menuitem to the menubook
        self.menubook.add(menu)

    async def load_menu(
        self,
        menu: Union[List[menuitem], MenuItemList, str],
        title: str = "",
        menuname: str = "",
    ) -> None:
        """Load and show a menu managing hotkey bindings

        Parameters
        ----------
        menu : Union[List[menuitem], MenuItemList, str]
            The menu details to load.  If:
                List[menuitem]: use the List, title, and menuname
                MenuItemList: use the MenuItemList
                str: Lookup the str in the menubook and use that menu
        title : str, optional
            Menu title, only needed when not using a MenuItemList, by default ""
        menuname : str, optional
            Menuname, only needed when not using a MenuItemList, by default ""
        """
        if isinstance(menu, str):
            menu = self.menubook.get_menu(menu)

        # push current menu and bindings onto the stack
        # the pre-menu state will have menuname = None
        self.menu_stack.append(
            (self.menuname, self._menu_items, self.title, self.app.bindings)
        )

        # build and show the new menu
        if isinstance(menu, MenuItemList) is False:
            menu = MenuItemList(menuname, menu, title)

        self._menu_items = menu.items
        self.title = menu.title
        self.menuname = menu.name

        self.skip_rows = 0
        self.index = 0

        # Bind the hotkeys in the new ment
        await self._bind_current_menu()

        # Resize menu
        self._resize_menu()

        self.visible = True

        if self.refresh_callback is not None:
            self.refresh_callback()

    def _resize_menu(self) -> None:
        """Calculate new menu size based on entries"""

        HOTKEY_PADDING = 4
        MENU_CHROME = 5

        # Adjust menu size to longest needed
        longest_desc_len = 0
        for item in self._menu_items:
            if item is None:
                continue
            longest_desc_len = max(longest_desc_len, len(item[1]))
        longest_desc_len = longest_desc_len + HOTKEY_PADDING + MENU_CHROME
        longest_desc_len = max(longest_desc_len, len(self.title) + MENU_CHROME)

        self.layout_size = (
            longest_desc_len if longest_desc_len < self.max_size else self.max_size
        )

    async def _bind_current_menu(self) -> None:
        # Rebind hotkeys to new menu
        self.app.bindings = Bindings()
        await self.app.bind("ctrl+c", "quit", show=False)
        await self.app.bind("escape", "menu_escape", show=False)
        await self.app.bind("down", "menu.menu_down", show=False)
        await self.app.bind("up", "menu.menu_up", show=False)
        await self.app.bind("enter", "menu.menu_enter", show=False)
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

        self.skip_rows = 0
        self.index = 0
        self._bind_current_menu()
        self._resize_menu()

        if self.menuname is None:
            self.visible = False

        if self.refresh_callback is not None:
            self.refresh_callback()

    # def menu_down(self) -> None:
    #     while True:
    #         if self.index == len(self._menu_items):
    #             self.index = 1
    #         else:
    #             self.index += 1
    #         if self._menu_items[self.index - 1] is not None:
    #             break

    # def menu_up(self) -> None:
    #     while True:
    #         if self.index == 0 or self.index == 1:
    #             self.index = len(self._menu_items)
    #         else:
    #             self.index -= 1
    #         if self._menu_items[self.index - 1] is not None:
    #             break

    # def menu_choose(self) -> Optional[str]:
    #     if self.index == 0:
    #         return None
    #     # return the callback for the entry
    #     return self._menu_items[self.index - 1][2]

    async def action_menu_enter(self) -> None:
        if self.index == 0:
            return None
        await self.app.action(self._menu_items[self.index - 1][2])
        # callback = self._menu_items[self.index - 1][2]
        # if callback is not None:
        #     # call the action directly
        #     target, params = textual.actions.parse(callback)
        #     action_target = getattr(self, f"action_{target}")
        #     await action_target(*params)

    async def action_load_menu(self, menuname: str) -> None:
        await self.load_menu(menuname)

    async def action_menu_up(self) -> None:
        while True:
            if self.index == 0 or self.index == 1:
                self.index = len(self._menu_items)
            else:
                self.index -= 1
            if self._menu_items[self.index - 1] is not None:
                break

    async def action_menu_down(self) -> None:
        while True:
            if self.index == len(self._menu_items):
                self.index = 1
            else:
                self.index += 1
            if self._menu_items[self.index - 1] is not None:
                break

    async def action_menu_backout(self) -> None:
        """Back out to previous menu"""
        await self.pop_menu()

    async def action_menu_escape(self) -> None:
        await self.pop_menu(pop_all=True)

    def render(self) -> RenderableType:
        MENU_CHROME = 4  # Unusable space in the menu for titles and padding
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
