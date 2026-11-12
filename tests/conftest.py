import pytest


@pytest.fixture(scope="session")
def qapp():
    """One QApplication for the whole test run (Qt allows only one, and widgets need the GUI kind)."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
