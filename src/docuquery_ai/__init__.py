"""Top-level package for the lightweight DocuQuery AI client."""

__all__ = ["DocumentQueryClient", "Settings"]

__version__ = "0.1.0"
__author__ = "DocuQuery AI Team"
__email__ = "contact@docuquery-ai.com"

# Import minimal components to avoid pulling in heavy optional dependencies at
# import time.  Additional modules can still be accessed via their subpackages
# when required by applications.
from .client import DocumentQueryClient  # noqa: E402
from .core.config import Settings  # noqa: E402

