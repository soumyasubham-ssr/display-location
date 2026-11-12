"""Single-instance guard and resource paths (TASK-004)."""

import subprocess
import sys
import time
import uuid

from display_location.resources import icon_path
from display_location.single_instance import SingleInstance, server_name


def _pump(qapp, until, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end and not until():
        qapp.processEvents()
        time.sleep(0.01)
    return until()


def _name():
    return f"DisplayLocation-test-{uuid.uuid4().hex[:8]}"


def _second_instance(qapp, name):
    """Run notify_running() in a separate process (like a real second launch) while
    this process keeps its event loop turning. Returns the child's stdout."""
    code = (
        "import sys; from PySide6.QtCore import QCoreApplication; "
        "from display_location.single_instance import SingleInstance; "
        "app = QCoreApplication([]); "
        f"print(SingleInstance({name!r}).notify_running())"
    )
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    _pump(qapp, lambda: proc.poll() is not None, timeout=15)
    out, _ = proc.communicate(timeout=5)
    return out.strip()


def test_icon_file_exists():
    assert icon_path().is_file()
    assert icon_path().name == "icon.ico"


def test_server_name_is_per_user_and_safe(monkeypatch):
    monkeypatch.setenv("USERNAME", "Jo Doe\\x")
    assert server_name() == "DisplayLocation-Jo_Doe_x"


def test_no_server_means_not_running(qapp):
    assert SingleInstance(_name()).notify_running() is False


def test_second_instance_sends_show(qapp):
    name = _name()
    first = SingleInstance(name)
    got = []
    first.show_requested.connect(lambda: got.append(True))
    assert first.listen()

    assert _second_instance(qapp, name) == "True"
    assert _pump(qapp, lambda: got), "first instance never received 'show'"
    first.close()


def test_restart_after_killed_instance(qapp):
    """A killed instance (Task Manager) must not block the next start."""
    name = _name()
    code = (
        "from PySide6.QtCore import QCoreApplication; "
        "from display_location.single_instance import SingleInstance; "
        "app = QCoreApplication([]); s = SingleInstance(" + repr(name) + "); "
        "print(s.listen(), flush=True); app.exec()"
    )
    victim = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert victim.stdout.readline().strip() == "True"
    victim.kill()  # like End task: no clean shutdown
    victim.wait(timeout=5)
    victim.stdout.close()

    # The venv python.exe is a launcher; its real interpreter child dies a moment later.
    fresh = SingleInstance(name)
    deadline = time.monotonic() + 3
    while fresh.notify_running() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert fresh.notify_running() is False  # nothing alive answers any more
    got = []
    fresh.show_requested.connect(lambda: got.append(True))
    assert fresh.listen()
    assert _second_instance(qapp, name) == "True"
    assert _pump(qapp, lambda: got)
    fresh.close()
