"""Tests for Engine backend selection and error when unavailable."""

import os

import pytest

from chitin import ChitinError, Engine


def test_engine_raises_when_both_backends_unavailable() -> None:
    """When lib cannot be loaded and CHITIN_SIDECAR_URL is unset, ChitinError is raised."""
    sidecar = os.environ.pop("CHITIN_SIDECAR_URL", None)
    lib_path = os.environ.pop("CHITIN_LIB_PATH", None)
    try:
        # Point at an existing non-library file so resolve returns it but CDLL fails
        fake_lib = os.path.abspath(__file__)
        os.environ["CHITIN_LIB_PATH"] = fake_lib
        with pytest.raises(ChitinError) as exc_info:
            Engine()
        assert "CHITIN_SIDECAR_URL" in str(exc_info.value)
    finally:
        if sidecar is not None:
            os.environ["CHITIN_SIDECAR_URL"] = sidecar
        if lib_path is not None:
            os.environ["CHITIN_LIB_PATH"] = lib_path
        else:
            os.environ.pop("CHITIN_LIB_PATH", None)
