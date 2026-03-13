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


def test_auto_theme_live_update():
    """Auto theme must listen for system color-scheme changes via matchMedia."""
    src = _source()
    assert "matchMedia" in src
    assert "addEventListener" in src
    assert "removeEventListener" in src
    # The handler should react to the correct media query and event
    assert "prefers-color-scheme: dark" in src
    assert '"change"' in src or "'change'" in src


def test_keyboard_accessibility_aria_labels():
    """Interactive elements must carry descriptive aria-label attributes."""
    src = _source()
    assert 'aria-label="Close chat"' in src
    assert 'aria-label="Type your message"' in src
    assert 'aria-label="Send message"' in src
    # Toggle button has dynamic aria-label
    assert "Open portfolio chat" in src
    assert "Close portfolio chat" in src


def test_toggle_button_aria_expanded():
    """Toggle button must expose aria-expanded to communicate open/closed state."""
    src = _source()
    assert "aria-expanded" in src


def test_messages_container_accessible():
    """Messages container must have role='log' and aria-live='polite'."""
    src = _source()
    assert 'role="log"' in src
    assert 'aria-live="polite"' in src


def test_error_state_role_alert():
    """Error message must use role='alert' so screen readers announce it."""
    src = _source()
    assert 'role="alert"' in src


def test_esc_key_closes_chat():
    """Pressing Escape must close the chat window."""
    src = _source()
    assert "Escape" in src
    # Escape handler must call setOpen(false)
    assert "setOpen(false)" in src or 'setOpen(false)' in src


def test_sources_rendered_as_links():
    """Source repos must be rendered as clickable anchor tags."""
    src = _source()
    assert "<a" in src
    assert "github.com" in src
    assert "target" in src
    assert "rel" in src


def test_input_auto_focus_on_open():
    """Input field must be focused automatically when the chat is opened."""
    src = _source()
    assert "inputRef" in src
    assert "focus()" in src
