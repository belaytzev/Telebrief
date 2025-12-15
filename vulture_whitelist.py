"""
Whitelist for Vulture - intentionally unused code.

This file lists code that Vulture might flag as unused but is actually
intentional (e.g., main functions, future features, API compatibility).
"""

# Entry point functions (called via if __name__ == "__main__")
_.main  # Used as entry point in multiple modules

# Test/debug functions
_.test_  # Test functions are called by pytest

# Private methods that might appear unused
_._format_messages_for_prompt  # Used internally in class

# Configuration attributes that might appear unused
_.temperature  # Configuration attribute
_.max_tokens  # Configuration attribute

# Telegram bot handler signatures require 'context' parameter even if unused
_.context  # Required by python-telegram-bot handler signature
