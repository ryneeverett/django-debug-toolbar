import django

if django.VERSION[:2] < (1, 6):     # unittest-style discovery isn't available
    from .commands.test_debugsqlshell import *                          # noqa
    from .panels.test_cache import *                                    # noqa
    from .panels.test_logging import *                                  # noqa
    from .panels.test_profiling import *                                # noqa
    from .panels.test_redirects import *                                # noqa
    from .panels.test_request import *                                  # noqa
    from .panels.test_sql import *                                      # noqa
    from .panels.test_template import *                                 # noqa
    from .test_integration import *                                     # noqa
    from .test_utils import *                                           # noqa
