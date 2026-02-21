"""Setup script for platform-specific wheels that bundle the shared library.
Used only by CI; do not use for the pure wheel (use pyproject.toml + build).
"""
from setuptools import Distribution, setup


class PlatformDistribution(Distribution):
    """Forces setuptools to tag the wheel as platform-specific (not py3-none-any)."""

    def has_ext_modules(self) -> bool:
        return True


setup(
    name="chitin-engine-lib",
    version="0.1.0",
    description="Python bindings for the Chitin security engine",
    license="Apache-2.0",
    python_requires=">=3.11",
    packages=["chitin"],
    package_data={"chitin": ["_lib/*", "py.typed"]},
    distclass=PlatformDistribution,
    url="https://github.com/datagoboom/chitin-engine-lib",
)
