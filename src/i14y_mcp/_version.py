"""The one place this package resolves its own version.

Read from the INSTALLED distribution's metadata, never written by hand. A
literal is a second copy of a number the build decides, and second copies
drift — `swiss-procurement-mcp` announced `0.4.0` to simap.ch while the package
on PyPI was `0.18.3`, fourteen minor versions later, from exactly such a
constant.

A module of its own, rather than resolving it in ``__init__``, so that
``client`` can import the version without importing the package root. The root
imports ``server``, which imports ``client``; taking the version from the
partially-initialised root would work only as long as nobody reorders two lines
in ``__init__``. ``bag-health-mcp`` has a latent circular import from precisely
that kind of arrangement.

The fallback marks itself as one: a PEP 440 local segment after ``+`` can never
be mistaken for a release, unlike a plausible-looking ``0.0.0``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("i14y-mcp")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0.0.0+source"

__all__ = ["__version__"]
