# Copyright 2018 miruka
# This file is part of harmonyqt, licensed under GPLv3.

import sys
from pathlib import Path
from typing import List, Optional

from matrix_client.client import MatrixClient
from matrix_client.room import Room
from pkg_resources import resource_filename
# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QDockWidget,
                             QMainWindow, QTabWidget)

from . import __about__, accounts, chat, events, homepage, usertree
from .caches import DISPLAY_NAMES

STYLESHEET = resource_filename(__about__.__name__, "stylesheet.qss")


class HarmonyQt(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.accounts = accounts.AccountManager(self)
        self.events   = events.EventManager(self)

        self.setWindowTitle(__about__.__pkg_name__)
        screen = QDesktopWidget().screenGeometry()
        self.resize(min(screen.width(), 800), min(screen.height(), 600))
        # self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.8)
        self.setStyleSheet(Path(STYLESHEET).read_text())

        self.setDockNestingEnabled(True)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        # self.setTabShape(QTabWidget.Triangular)

        self.tree_dock = QDockWidget("Accounts", self)
        self.tree_dock.setWidget(usertree.UserTree(self))
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tree_dock)

        self.home_dock = QDockWidget("Home", self)
        self.home_dock.setWidget(homepage.HomePage())
        self.home_dock.setFeatures(
            # Make it unclosable so we can always rely on it to append tabs
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.home_dock)

        self.chat_docks = []

        self.show()
        try:
            self.accounts.login_using_config()
        except FileNotFoundError:
            pass



    def go_to_chat_dock(self, client: MatrixClient, room: Room) -> None:
        def go(dock: QDockWidget) -> None:
            dock.show()
            dock.raise_()
            dock.widget().sendbox.setFocus()

        for dock in self.chat_docks:
            if dock.widget().room == room and dock.widget().client == client:
                go(dock)
                return

        chat_ = chat.Chat(window=self, client=client, room=room)
        dock  = QDockWidget(f"{DISPLAY_NAMES.user(client)}/"
                            f"{DISPLAY_NAMES.room(room)}",
                            self)
        dock.setWidget(chat_)
        self.tabifyDockWidget(self.home_dock, dock)
        go(dock)
        self.chat_docks.append(dock)


    def remove_chat_dock(self, client: MatrixClient, room: Room) -> None:
        for i, dock in enumerate(self.chat_docks):
            if dock.widget().room.room_id   == room.room_id and \
               dock.widget().client.user_id == client.user_id:
                dock.hide()
                del self.chat_docks[i]


def run(argv: Optional[List[str]] = None) -> None:
    app = QApplication(argv or sys.argv)
    _   = HarmonyQt()

    # Make CTRL-C work
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    sys.exit(app.exec_())
