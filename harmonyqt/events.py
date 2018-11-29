# Copyright 2018 miruka
# This file is part of harmonyqt, licensed under GPLv3.

import time
from queue import Queue
from threading import Lock, Thread
from typing import Dict, List, Tuple

from matrix_client.client import MatrixClient
from matrix_client.room import Room
from matrix_client.user import User
# pylint: disable=no-name-in-module
from PyQt5.QtWidgets import QMainWindow


class EventManager:
    def __init__(self, window: QMainWindow) -> None:
        self.window = window
        # self.messages[client.user_id[room.room_id[Queue[event]]]
        self.messages: Dict[str, Dict[str, Queue]] = {}
        # (user_id, room_id)
        self.added_rooms: List[Tuple[str, str]] = []

        self._lock = Lock()

        self.window.accounts.signal.login.connect(self.add_account)


    def add_account(self, client: MatrixClient) -> None:
        "Setup event listeners for client. Called from AccountManager.login()."
        self.messages[client.user_id] = {}

        Thread(target=self.watch_rooms, args=(client,), daemon=True).start()

        client.add_listener(lambda ev, c=client: self.on_event(c, ev))

        client.add_presence_listener(
            lambda ev, c=client: self.on_presence_event(c, ev))

        client.add_ephemeral_listener(
            lambda ev, c=client: self.on_ephemeral_event(c, ev))

        client.add_invite_listener(
            lambda rid, state, c=client: self.on_invite_event(c, rid, state))

        client.add_leave_listener(
            lambda rid, room, c=client: self.on_leave_event(c, rid, room))

        client.start_listener_thread()

        # TODO: room.add_state_listener


    def watch_rooms(self, client: MatrixClient) -> None:
        # join events aren't all published/caught using a normal listener
        tree = self.window.tree_dock.widget()

        while True:
            # tuple() to prevent problems if dict changes size during iteration
            for room in tuple(client.rooms.values()):
                if (client.user_id, room.room_id) in self.added_rooms:
                    continue

                tree.add_room(client=client, room=room)
                self.added_rooms.append((client.user_id, room.room_id))

            time.sleep(0.2)


    def on_event(self, client: MatrixClient, event: dict) -> None:
        ev    = event
        etype = event["type"]

        with self._lock:
            if etype != "m.room.message":
                _log("blue", client.user_id, ev)

            if etype == "m.room.message":
                msg_events = self.messages[client.user_id]

                if ev["room_id"] not in msg_events:
                    msg_events[ev["room_id"]] = Queue()

                msg_events[ev["room_id"]].put(ev)


    # pylint: disable=no-self-use

    def on_presence_event(self, client: MatrixClient, event: dict) -> None:
        with self._lock:
            _log("yellow", client.user_id, event)


    def on_ephemeral_event(self, client: MatrixClient, event: dict) -> None:
        with self._lock:
            _log("purple", client.user_id, event)


    def on_invite_event(self, client: MatrixClient, room_id: int, state: dict
                       ) -> None:
        self.window.tree_dock.widget().add_room(
            client    = client,
            room      = Room(client, room_id),
            invite_by = User(client, state["events"][-1]["sender"])
        )
        self.added_rooms.append((client.user_id, room_id))


    def on_leave_event(self, client: MatrixClient, room_id: int, _: dict
                      ) -> None:
        room = Room(client, room_id)
        self.window.tree_dock.widget().remove_room(client, room)
        self.window.remove_chat_dock(client, room)

        for i, (uid, rid) in enumerate(self.added_rooms):
            if client.user_id == uid and room_id == rid:
                del self.added_rooms[i]


def _log(color: str, *args) -> None:
    import json
    args = [json.dumps(arg, indent=4, sort_keys=True) for arg in args]
    nums = {"black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4,
            "purple": 5, "magenta": 5, "cyan": 6, "white": 7, "gray": 7}
    print(f"\033[3{nums[color]}m", *args, "\033[0m", sep="\n", end="\n\n")
