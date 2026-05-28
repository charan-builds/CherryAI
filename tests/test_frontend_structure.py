from frontend.styles.theme import load_stylesheet
from frontend.windows.main_window import SECTIONS


def test_frontend_navigation_sections_are_defined():
    labels = [section.title for section in SECTIONS]

    assert labels == [
        "Dashboard",
        "Tasks",
        "Study Mode",
        "Memory",
        "Analytics",
        "Settings",
    ]


def test_dark_theme_stylesheet_loads():
    stylesheet = load_stylesheet("dark_theme")

    assert "QFrame#Sidebar" in stylesheet
    assert "QPushButton#SendButton" in stylesheet
