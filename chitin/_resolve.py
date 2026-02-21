"""Resolve path to the chitin shared library."""

import os
import platform
from pathlib import Path

# Library filename for current platform
_LIB_NAMES = {
    "Linux": "libchitin.so",
    "Darwin": "libchitin.dylib",
    "Windows": "chitin.dll",
}


def _lib_name() -> str:
    return _LIB_NAMES.get(platform.system(), "libchitin.so")


def resolve_chitin_lib() -> str:
    """
    Resolve path to the chitin shared library.

    Order:
    1. CHITIN_LIB_PATH environment variable (explicit path)
    2. chitin/_lib/ inside the installed package (bundled in platform wheel)
    3. ./target/release/{lib_name} (dev: building engine locally)
    4. ../chitin-engine/target/release/{lib_name} (dev: sibling repo)
    5. System library search path (return lib name only)

    Returns a path string or the library name for CDLL. Caller must try
    ctypes.CDLL(result); on OSError, raise with a helpful message.
    """
    lib_name = _lib_name()

    # 1. Explicit path
    env_path = os.environ.get("CHITIN_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    # 2. Bundled in platform wheel (chitin/_lib/ next to this file)
    bundled = Path(__file__).resolve().parent / "_lib" / lib_name
    if bundled.exists():
        return str(bundled)

    # 3. Dev: local target/release
    dev_cwd = Path.cwd() / "target" / "release" / lib_name
    if dev_cwd.is_file():
        return str(dev_cwd)

    # 4. Dev: sibling chitin-engine repo (chitin-engine-lib/../chitin-engine/target/release/)
    _repo_root = Path(__file__).resolve().parent.parent
    sibling = _repo_root.parent / "chitin-engine" / "target" / "release" / lib_name
    if sibling.is_file():
        return str(sibling)

    # 5. System search (LD_LIBRARY_PATH, DYLD_LIBRARY_PATH, PATH)
    return lib_name


def _load_lib_error_message() -> str:
    return (
        "Could not load the Chitin shared library. Either set CHITIN_LIB_PATH to the full path "
        "to libchitin.so / libchitin.dylib / chitin.dll, install a platform-specific wheel "
        "(chitin_engine_lib-*-manylinux_*.whl, etc.) that bundles the library, or set "
        "CHITIN_SIDECAR_URL to use the HTTP sidecar instead."
    )
