"""One instance per user (FR-13, D-010): a second launch asks the first to show its popup."""

from __future__ import annotations

import logging
import os
import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger("display_location.single_instance")

SHOW_MESSAGE = b"show"
CONNECT_TIMEOUT_MS = 300


def server_name() -> str:
    user = re.sub(r"[^A-Za-z0-9_.-]", "_", os.environ.get("USERNAME", "user"))
    return f"DisplayLocation-{user}"


class SingleInstance(QObject):
    """Call ``notify_running()`` first; if it returns False, call ``listen()``."""

    show_requested = Signal()

    def __init__(self, name: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.name = name or server_name()
        self._server: QLocalServer | None = None

    def notify_running(self) -> bool:
        """True if another instance is running (it has been sent "show")."""
        sock = QLocalSocket()
        sock.connectToServer(self.name)
        if not sock.waitForConnected(CONNECT_TIMEOUT_MS):
            return False
        sock.write(SHOW_MESSAGE)
        sock.flush()
        sock.waitForBytesWritten(CONNECT_TIMEOUT_MS)
        sock.disconnectFromServer()
        log.info("Another instance is running; sent %r", SHOW_MESSAGE)
        return True

    def listen(self) -> bool:
        # Clears a stale pipe left by a killed process (ARCHITECTURE §11).
        QLocalServer.removeServer(self.name)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        ok = self._server.listen(self.name)
        if ok:
            log.info("Single-instance server listening on %s", self.name)
        else:
            log.error("Single-instance server failed to listen: %s", self._server.errorString())
        return ok

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def _on_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._on_ready(s))
            sock.disconnected.connect(sock.deleteLater)
            if sock.bytesAvailable():
                self._on_ready(sock)

    def _on_ready(self, sock: QLocalSocket) -> None:
        data = bytes(sock.readAll().data()).strip()
        if not data:
            return
        log.info("Received %r from a second instance", data)
        if data == SHOW_MESSAGE:
            self.show_requested.emit()
