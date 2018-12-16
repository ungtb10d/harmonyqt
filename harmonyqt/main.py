# Copyright 2018 miruka
# This file is part of harmonyqt, licensed under GPLv3.

from typing import Dict, Optional, Tuple

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent, QMouseEvent
from PyQt5.QtWidgets import (
    QDesktopWidget, QDockWidget, QLabel, QMainWindow, QTabWidget, QWidget
)

from . import (
    __about__, accounts, chat, events, homepage, main_window, messages,
    theming, toolbar, usertree
)


class DockTitleBar(QLabel):
    # pylint: disable=invalid-name
    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)

        if event.button() == Qt.MiddleButton:
            self.parent().hide()


class Dock(QDockWidget):
    def __init__(self, title: str, parent: QWidget, title_bar: bool = False
                ) -> None:
        super().__init__(title, parent)
        self.title_bar:       DockTitleBar   = DockTitleBar(title, self)
        self.title_bar_shown: Optional[bool] = None
        self.show_title_bar(title_bar)


    def show_title_bar(self, show: Optional[bool] = None) -> None:
        if show is None:
            show = not self.title_bar_shown

        self.setTitleBarWidget(self.title_bar if show else QWidget())
        self.title_bar_shown = show


    def focus(self) -> None:
        self.show()
        self.raise_()


class ChatDock(Dock):
    def __init__(self, user_id: str, room_id: str, parent: QWidget,
                 title_bar: bool = False) -> None:
        self.user_id: str = user_id
        self.room_id: str = room_id
        super().__init__(self.title, parent, title_bar)
        self.change_room(self.user_id, self.room_id)


    @property
    def title(self) -> str:
        client = main_window().accounts[self.user_id]
        return ": ".join((
            client.h_user.get_display_name(),
            client.rooms[self.room_id].display_name
        ))


    def update_title(self) -> None:
        self.setWindowTitle(self.title)


    def change_room(self, to_user_id: str, to_room_id: str) -> None:
        self.chat = chat.Chat(to_user_id, to_room_id)
        self.user_id, self.room_id = to_user_id, to_room_id
        self.setWidget(self.chat)
        self.update_title()


class HarmonyQt(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.title_bars_shown       = False
        self.alt_title_bars_toggled = False


    def construct(self) -> None:
        # pylint: disable=attribute-defined-outside-init
        # Can't define all that __init__ instead.
        # The UI elements need _MAIN_WINDOW to be set, see run() in __init__.


        # Setup appearance:
        self.setWindowTitle("Harmony")
        screen = QDesktopWidget().screenGeometry()
        self.resize(min(screen.width(), 800), min(screen.height(), 600))

        # self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.9)

        self.theme = theming.Theme("glass")
        self.icons = theming.Icons("flat_white")

        self.setStyleSheet(self.theme.style("interface"))


        # Setup main classes and event listeners:

        self.accounts = accounts.AccountManager()
        self.events   = events.EventManager()
        self.messages = messages.MessageProcessor()

        self.events.signal.left_room.connect(self.remove_chat_dock)
        self.events.signal.room_rename.connect(self.update_chat_dock_name)
        # Triggered by room renames that happen when account changes
        # self.events.signal.account_change.connect(self.update_chat_dock_name)


        # Setup docks:

        self.setDockNestingEnabled(True)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        # self.setTabShape(QTabWidget.Triangular)

        self.tree_dock = Dock("Accounts", self)
        self.tree_dock.setWidget(usertree.UserTree())
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tree_dock)

        self.home_dock = Dock("Home", self)
        self.home_dock.setWidget(homepage.HomePage())
        self.addDockWidget(Qt.RightDockWidgetArea, self.home_dock)

        # {(user_id, room_id): dock}
        self.chat_docks: Dict[Tuple[str, str], ChatDock] = {}

        self.actions_dock = Dock("Actions", self)
        self.actions_dock.setWidget(toolbar.ActionsBar())
        self.addDockWidget(
            Qt.LeftDockWidgetArea, self.actions_dock, Qt.Vertical
        )


        # Run:

        self.show()

        try:
            self.accounts.login_using_config()
        except FileNotFoundError:
            pass


    def show_dock_title_bars(self, show: Optional[bool] = None) -> None:
        if show is None:
            show = not self.title_bars_shown

        docks = (self.tree_dock, self.actions_dock, self.home_dock,
                 *self.chat_docks.values())

        for dock in docks:
            dock.show_title_bar(show)

        self.title_bars_shown = show


    def go_to_chat_dock(self, user_id: str, room_id: str) -> None:
        dock = self.chat_docks.get((user_id, room_id))
        if dock:
            dock.focus()
            return

        dock = ChatDock(user_id, room_id, self, self.title_bars_shown)
        self.tabifyDockWidget(self.home_dock, dock)
        self.chat_docks[(user_id, room_id)] = dock
        dock.focus()


    def remove_chat_dock(self, user_id: str, room_id: str) -> None:
        dock = self.chat_docks.get((user_id, room_id))
        if dock:
            dock.hide()
            del self.chat_docks[(user_id, room_id)]


    def update_chat_dock_name(self, user_id: str, room_id: str) -> None:
        dock = self.chat_docks.get((user_id, room_id))
        if dock:
            dock.update_title()


    # pylint: disable=invalid-name
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self.title_bars_shown and not self.alt_title_bars_toggled and \
           event.key() == Qt.Key_Alt:
            self.show_dock_title_bars(True)
            self.alt_title_bars_toggled = True


    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if self.alt_title_bars_toggled and event.key() == Qt.Key_Alt:
            self.show_dock_title_bars(False)
            self.alt_title_bars_toggled = False
