from .pagination import PAGES as PAGINATION_PAGES
from .config import PAGES as CONFIG_PAGES
from .proxy import PAGES as PROXY_PAGES
from .help import PAGES as HELP_PAGES
from .base import PAGES as BASE_PAGES
from .edit import PAGES as EDIT_PAGES
from .bio import PAGES as BIO_PAGES


__all__ = (
    'PAGES',
)


PAGES = (
    PAGINATION_PAGES |
    CONFIG_PAGES |
    PROXY_PAGES |
    HELP_PAGES |
    BASE_PAGES |
    EDIT_PAGES |
    BIO_PAGES
)
