"""Feature flag implementation.

T6 deliverable. The actual storage backend (env var, config file, central flag
service) is a PAIQ infrastructure concern; this module exposes a single
interface that the rest of the code uses.

Implemented: env-var shim (PAIQ_D_EXTRACTION_ENABLED). Production routes through
PAIQ's central flag service.
"""

from __future__ import annotations

import os


D_EXTRACTION_FLAG = "paiq.d_extraction.enabled"


def is_d_enabled() -> bool:
    """Return True if D's modified extraction is enabled.

    Reads from env var `PAIQ_D_EXTRACTION_ENABLED` (case-insensitive: true/1/yes).
    Real implementation routes through PAIQ's central flag service; env var is
    the local-dev / test override.

    T6 deliverable.
    """
    val = os.environ.get("PAIQ_D_EXTRACTION_ENABLED", "false").strip().lower()
    return val in {"true", "1", "yes"}


def set_d_enabled(enabled: bool) -> None:
    """Set the flag locally (for testing only).

    Real production flag flips go through the central flag service, NOT this
    function.
    """
    os.environ["PAIQ_D_EXTRACTION_ENABLED"] = "true" if enabled else "false"
