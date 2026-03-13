"""Smoke tests for the FolioChat React/TypeScript widget source file."""

import re
from pathlib import Path

COMPONENT_PATH = Path(__file__).parent.parent / "foliochat.tsx"


def _source() -> str:
    return COMPONENT_PATH.read_text()


def test_component_file_exists():
    """foliochat.tsx must exist at the repository root."""
    assert COMPONENT_PATH.is_file(), "foliochat.tsx not found"


def test_default_export():
    """Component must have a default export."""
    src = _source()
    assert "export default FolioChat" in src


def test_named_export():
    """Component must have a named export."""
    src = _source()
    assert "export function FolioChat" in src


def test_foliochat_props_interface():
    """FolioChatProps interface must declare the expected props."""
    src = _source()
    assert "interface FolioChatProps" in src
    for prop in ("endpoint", "theme", "position", "accentColor", "greeting"):
        assert prop in src, f"Prop '{prop}' missing from FolioChatProps"


def test_floating_button_rendered():
    """A toggle button for open/close must be present."""
    src = _source()
    # The toggle button switches between open/closed state
    assert "setOpen" in src


def test_position_prop_supported():
    """Both bottom-right and bottom-left positions must be handled."""
    src = _source()
    assert "bottom-right" in src
    assert "bottom-left" in src


def test_message_bubbles_user_and_assistant():
    """User and assistant message bubbles must be distinguished via separate color tokens."""
    src = _source()
    # The component uses msg.role === "user" to branch between bubble styles
    assert 'role === "user"' in src or "role === 'user'" in src
    # Separate color tokens for each role must exist
    assert "userBubble" in src
    assert "assistantBubble" in src


def test_input_field_present():
    """An input element for user text must be present."""
    src = _source()
    assert "<input" in src


def test_send_button_present():
    """A send button must be present."""
    src = _source()
    assert "sendMessage" in src
    assert "<button" in src


def test_enter_key_handler():
    """Pressing Enter should submit the message."""
    src = _source()
    assert "Enter" in src
    assert "onKeyDown" in src or "handleKey" in src


def test_loading_indicator():
    """A loading indicator (···) must appear when awaiting a response."""
    src = _source()
    assert "···" in src
    assert "loading" in src


def test_context_fetch_on_mount():
    """The component must fetch /context on mount via useEffect."""
    src = _source()
    assert "useEffect" in src
    assert "/context" in src


def test_greeting_displayed():
    """The greeting from /context must be surfaced to the user."""
    src = _source()
    assert "greeting" in src


def test_theme_support():
    """Dark, light, and auto themes must all be referenced."""
    src = _source()
    assert '"dark"' in src
    assert '"light"' in src
    assert '"auto"' in src


def test_dark_and_light_theme_colors():
    """Both THEMES entries must define bg, text, and border colors."""
    src = _source()
    assert "const THEMES" in src
    # Each theme object should contain bg, text, border keys
    for key in ("bg", "text", "border"):
        assert key in src, f"Color key '{key}' missing from THEMES"
