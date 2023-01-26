from typing import Union, Tuple, List, Optional, Callable
from textual.widgets import Static
from textual.app import App
from textual.reactive import Reactive
from textual.binding import Bindings
from textual.message import Message, MessageTarget
from textual import log
import textual.actions
from rich.console import RenderableType
from rich.table import Table
from rich.panel import Panel
from rich.style import StyleType, Style
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


class Menu(Static):

    # Reactives are descriptors, so need to be defined as class variables
    index: Reactive[int] = Reactive(0)
    _show_menu = Reactive(False, always_update=True)

    COMPONENT_CLASSES = {
        "menu--style",
        "menu--key-style",
        "menu--key-description-style",
    }

    def __init__(
        self,
        arg1: Union[list[menuitem], MenuItemList] = None,
        title: str = "",
        refresh_callback: Callable = None,
        max_size: int = 50,
        **kwargs,
    ) -> None:
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
        self.max_size = max_size

        # keep an internal menubook
        self.menubook = MenuBook()

        # stack for storing cascading menus and bindings
        self._focuslist = []
        self._focus_save = None
        self._menu_stack = []

    class FocusMessage(Message):
        """Message to inform the app that Focus has been taken"""

        def __init__(self, sender: MessageTarget, focustaken=True) -> None:
            self.focustaken = focustaken
            super().__init__(sender)

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

    def load_menu(
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
        self._menu_stack.append(
            (self.menuname, self._menu_items, self.title, self.app._bindings)
        )

        # build and show the new menu
        if isinstance(menu, MenuItemList) is False:
            menu = MenuItemList(menuname, menu, title)

        self._menu_items = menu.items
        self.title = menu.title
        self.menuname = menu.name

        self.skip_rows = 0
        self.index = 0

        # Bind the hotkeys in the new menu
        self._bind_current_menu()

        # Resize and show the menu
        self._resize_menu()
        self.show_menu()

        if self.refresh_callback is not None:
            self.refresh_callback()

    def show_menu(self) -> None:
        """Make the menu visible"""
        self._show_menu = True
        self._override_focus()

    def hide_menu(self) -> None:
        """Hide the menu"""
        self._show_menu = False
        self._restore_focus()

    def watch__show_menu(self, show_menu: bool) -> None:
        """Called when _show_menu is modified, toggle the class that shwos the menu"""
        self.app.set_class(show_menu, "-show-menu")

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

    def _bind_current_menu(self) -> None:
        # Rebind hotkeys to new menu
        self.app._bindings = Bindings()
        # self.app.bind("ctrl+c", "quit", show=False)
        self.bind("escape", "menu_escape", show=False)
        self.bind(".", "menu_escape", show=False)
        self.bind("down", "menu_down", show=False)
        self.bind("up", "menu_up", show=False)
        self.bind("enter", "menu_enter", show=False)
        for item in self._menu_items:
            if item is None:
                continue
            (chr, description, callback) = item
            self.bind(chr.lower(), callback)
            self.bind(chr.upper(), callback)

    def _override_focus(self):
        """remove focus for everything, force it to the dialog"""
        self._focus_save = self.app.focused
        for widget in self.app.screen.focus_chain:
            self._focuslist.append(widget)
            widget.can_focus = False
        self.can_focus = True
        self.focus()
        self.emit_no_wait(self.FocusMessage(self, focustaken=True))

    def _restore_focus(self):
        """restore focus to what it was before we stole it"""
        while len(self._focuslist) > 0:
            self._focuslist.pop().can_focus = True
        if self._focus_save is not None:
            self.app.set_focus(self._focus_save)
        self.emit_no_wait(self.FocusMessage(self, focustaken=False))

    async def pop_menu(self, pop_all=False) -> None:
        """Recover last menu and bindings"""
        if pop_all is True:
            """pop all until at the bottom"""
            while self.menuname is not None:
                (
                    self.menuname,
                    self._menu_items,
                    self.title,
                    self.app._bindings,
                ) = self._menu_stack.pop()
        else:
            (
                self.menuname,
                self._menu_items,
                self.title,
                self.app._bindings,
            ) = self._menu_stack.pop()

        self.skip_rows = 0
        self._resize_menu()
        self.index = 0

        if self.menuname is None:
            self.hide_menu()
        else:
            self.show_menu()

        if self.refresh_callback is not None:
            self.refresh_callback()

    async def action_menu_enter(self) -> None:
        if self.index == 0:
            return None
        if self._menu_items[self.index - 1][2][:3] == "app":
            await self.app.action(self._menu_items[self.index - 1][2])
        else:
            await self.action(self._menu_items[self.index - 1][2])

    def action_load_menu(self, menuname: str) -> None:
        self.load_menu(menuname)

    def action_menu_up(self) -> None:
        while True:
            if self.index == 0 or self.index == 1:
                self.index = len(self._menu_items)
            else:
                self.index -= 1
            if self._menu_items[self.index - 1] is not None:
                break

    def action_menu_down(self) -> None:
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
        # get styles
        menu_style = self.get_component_rich_style("menu--style")
        key_style = self.get_component_rich_style("menu--key-style")

        key_description_style = self.get_component_rich_style(
            "menu--key-description-style"
        )

        space_style = Style(bgcolor=menu_style.bgcolor, color=menu_style.bgcolor)

        MENU_CHROME = 4  # Unusable space in the menu for titles and padding
        menu_max_rows = self.size.height - MENU_CHROME
        subtitle = ""

        menu_table = Table.grid()
        menu_table.add_column("key", justify="left", width=3, style=key_style)
        menu_table.add_column("space", width=2, style=space_style)
        menu_table.add_column("action", justify="left", style=key_description_style)

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
                    menu_table.add_row(
                        f"({bind_chr})", "", description, style="reverse"
                    )
                else:
                    key_text = Text.assemble(
                        f"({bind_chr})",
                        meta={"@click": callback},
                    )
                    menu_table.add_row(key_text, "", description)
        menu = Panel(
            menu_table,
            title=self.title,
            style=menu_style,
            padding=(1, 1),
            subtitle=subtitle,
        )
        return menu

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
