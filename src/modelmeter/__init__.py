"""ModelMeter package."""

from modelmeter.cli.main import main
from modelmeter.common.version import get_product_version

__version__ = get_product_version()

__all__ = ["main", "__version__"]
