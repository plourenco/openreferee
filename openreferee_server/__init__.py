import configparser
import os


# read version from setup.cfg
parser = configparser.ConfigParser()
parser.read(os.path.join(os.path.dirname(__file__), "..", "setup.cfg"))

__version__ = parser["metadata"]["version"]

from .server import app  # noqa: E402, isort:skip

__all__ = ["app", "__version__"]
