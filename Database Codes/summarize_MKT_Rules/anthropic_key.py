"""Resolve the Anthropic API key from the Windows Credential Manager.

The key is read from the OS encrypted vault via `keyring`, so it never lives
in source, a .env, or the environment. Falls back to the ANTHROPIC_API_KEY
environment variable if the vault entry is absent.

Store the key once (you will be prompted to paste it, so it stays out of
shell history):

    keyring set anthropic ANTHROPIC_API_KEY
"""

import os
import keyring

SERVICE = "anthropic"
USERNAME = "ANTHROPIC_API_KEY"


def get_anthropic_key():
    key = keyring.get_password(SERVICE, USERNAME)
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "No Anthropic API key found.\n"
            "Store it once in the Windows Credential Manager with:\n"
            "    keyring set anthropic ANTHROPIC_API_KEY\n"
            "(or set the ANTHROPIC_API_KEY environment variable)."
        )
    return key
