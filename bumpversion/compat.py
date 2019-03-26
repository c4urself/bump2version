import codecs
import platform
import sys


IS_PY2 = sys.version_info[0] == 2
IS_PY3 = sys.version_info[0] == 3
IS_WINDOWS = platform.system() == "Windows"


def _command_args(args):
    if IS_WINDOWS and IS_PY2:
        return [a.encode("utf-8") for a in args]
    return args


if IS_PY2:
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    from StringIO import StringIO  # noqa # pylint: disable=import-error
    from ConfigParser import (  # noqa
        RawConfigParser,
        SafeConfigParser as ConfigParser,
        NoOptionError,
    )

elif IS_PY3:
    from io import StringIO  # noqa # pylint: disable=import-error

    # On Py2, "SafeConfigParser" is the same as "ConfigParser" on Py3
    from configparser import (  # noqa
        RawConfigParser,
        ConfigParser,
        NoOptionError,
    )
