# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import argparse
from datetime import datetime
import io
import logging
import os
import re
import sre_constants
import sys
import warnings

from bumpversion import __version__, __title__
from bumpversion.version_part import (
    VersionConfig,
    NumericVersionPartConfiguration,
    ConfiguredVersionPartConfiguration,
)
from bumpversion.compat import (
    ConfigParser,
    StringIO,
    RawConfigParser,
    NoOptionError,
)
from bumpversion.exceptions import (
    IncompleteVersionRepresentationException,
    MissingValueForSerializationException,
    WorkingDirectoryIsDirtyException,
)

from bumpversion.utils import (
    ConfiguredFile,
    DiscardDefaultIfSpecifiedAppendAction,
    keyvaluestring,
    prefixed_environ,
)
from bumpversion.vcs import Git, Mercurial


DESCRIPTION = "{}: v{} (using Python v{})".format(
    __title__,
    __version__,
    sys.version.split("\n")[0].split(" ")[0]
)
VCS = [Git, Mercurial]


logger_list = logging.getLogger("bumpversion.list")
logger = logging.getLogger(__name__)
time_context = {"now": datetime.now(), "utcnow": datetime.utcnow()}


OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES = [
    "--config-file",
    "--current-version",
    "--message",
    "--new-version",
    "--parse",
    "--serialize",
    "--search",
    "--replace",
    "--tag-name",
    "--tag-message",
    "-m",
]


def split_args_in_optional_and_positional(args):
    # manually parsing positional arguments because stupid argparse can't mix
    # positional and optional arguments

    positions = []
    for i, arg in enumerate(args):

        previous = None

        if i > 0:
            previous = args[i - 1]

        if (not arg.startswith("-")) and (
            previous not in OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES
        ):
            positions.append(i)

    positionals = [arg for i, arg in enumerate(args) if i in positions]
    args = [arg for i, arg in enumerate(args) if i not in positions]

    return (positionals, args)


def main(original_args=None):

    positionals, args = split_args_in_optional_and_positional(
        sys.argv[1:] if original_args is None else original_args
    )

    if len(positionals[1:]) > 2:
        warnings.warn(
            "Giving multiple files on the command line will be deprecated,"
            " please use [bumpversion:file:...] in a config file.",
            PendingDeprecationWarning,
        )

    parser1 = argparse.ArgumentParser(add_help=False)

    parser1.add_argument(
        "--config-file",
        metavar="FILE",
        default=argparse.SUPPRESS,
        required=False,
        help="Config file to read most of the variables from (default: .bumpversion.cfg)",
    )

    parser1.add_argument(
        "--verbose",
        action="count",
        default=0,
        help="Print verbose logging to stderr",
        required=False,
    )

    parser1.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List machine readable information",
        required=False,
    )

    parser1.add_argument(
        "--allow-dirty",
        action="store_true",
        default=False,
        help="Don't abort if working directory is dirty",
        required=False,
    )

    known_args, remaining_argv = parser1.parse_known_args(args)

    logformatter = logging.Formatter("%(message)s")

    if not logger_list.handlers:
        ch2 = logging.StreamHandler(sys.stdout)
        ch2.setFormatter(logformatter)
        logger_list.addHandler(ch2)

    if known_args.list:
        logger_list.setLevel(logging.DEBUG)

    try:
        log_level = [logging.WARNING, logging.INFO, logging.DEBUG][known_args.verbose]
    except IndexError:
        log_level = logging.DEBUG

    root_logger = logging.getLogger('')
    root_logger.setLevel(log_level)

    logger.debug("Starting %s", DESCRIPTION)

    defaults = {}
    vcs_info = {}

    for vcs in VCS:
        if vcs.is_usable():
            vcs_info.update(vcs.latest_tag_info())

    if "current_version" in vcs_info:
        defaults["current_version"] = vcs_info["current_version"]

    explicit_config = hasattr(known_args, "config_file")

    if explicit_config:
        config_file = known_args.config_file
    elif not os.path.exists(".bumpversion.cfg") and os.path.exists("setup.cfg"):
        config_file = "setup.cfg"
    else:
        config_file = ".bumpversion.cfg"

    # setup.cfg supports interpolation - for compatibility we must do the same.
    if os.path.basename(config_file) == "setup.cfg":
        config = ConfigParser("")
    else:
        config = RawConfigParser("")

    # don't transform keys to lowercase (which would be the default)
    config.optionxform = lambda option: option

    config.add_section("bumpversion")

    config_file_exists = os.path.exists(config_file)

    part_configs = {}

    files = []

    if config_file_exists:

        logger.info("Reading config file %s:", config_file)
        # TODO: this is a DEBUG level log
        with io.open(config_file, "rt", encoding="utf-8") as f:
            logger.info(f.read())
            config_new_lines = f.newlines

        try:
            # TODO: we're reading the config file twice.
            config.read_file(io.open(config_file, "rt", encoding="utf-8"))
        except AttributeError:
            # python 2 standard ConfigParser doesn't have read_file,
            # only deprecated readfp
            config.readfp(io.open(config_file, "rt", encoding="utf-8"))

        log_config = StringIO()
        config.write(log_config)

        if "files" in dict(config.items("bumpversion")):
            warnings.warn(
                "'files =' configuration will be deprecated, please use [bumpversion:file:...]",
                PendingDeprecationWarning,
            )

        defaults.update(dict(config.items("bumpversion")))

        for listvaluename in ("serialize",):
            try:
                value = config.get("bumpversion", listvaluename)
                defaults[listvaluename] = list(
                    filter(None, (x.strip() for x in value.splitlines()))
                )
            except NoOptionError:
                pass  # no default value then ;)

        for boolvaluename in ("commit", "tag", "dry_run"):
            try:
                defaults[boolvaluename] = config.getboolean(
                    "bumpversion", boolvaluename
                )
            except NoOptionError:
                pass  # no default value then ;)

        for section_name in config.sections():

            section_name_match = re.compile("^bumpversion:(file|part):(.+)").match(
                section_name
            )

            if not section_name_match:
                continue

            section_prefix, section_value = section_name_match.groups()

            section_config = dict(config.items(section_name))

            if section_prefix == "part":

                ThisVersionPartConfiguration = NumericVersionPartConfiguration

                if "values" in section_config:
                    section_config["values"] = list(
                        filter(
                            None,
                            (x.strip() for x in section_config["values"].splitlines()),
                        )
                    )
                    ThisVersionPartConfiguration = ConfiguredVersionPartConfiguration

                part_configs[section_value] = ThisVersionPartConfiguration(
                    **section_config
                )

            elif section_prefix == "file":

                filename = section_value

                if "serialize" in section_config:
                    section_config["serialize"] = list(
                        filter(
                            None,
                            (
                                x.strip().replace("\\n", "\n")
                                for x in section_config["serialize"].splitlines()
                            ),
                        )
                    )

                section_config["part_configs"] = part_configs

                if "parse" not in section_config:
                    section_config["parse"] = defaults.get(
                        "parse", r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
                    )

                if "serialize" not in section_config:
                    section_config["serialize"] = defaults.get(
                        "serialize", [str("{major}.{minor}.{patch}")]
                    )

                if "search" not in section_config:
                    section_config["search"] = defaults.get(
                        "search", "{current_version}"
                    )

                if "replace" not in section_config:
                    section_config["replace"] = defaults.get("replace", "{new_version}")

                files.append(ConfiguredFile(filename, VersionConfig(**section_config)))

    else:
        message = "Could not read config file at {}".format(config_file)
        if explicit_config:
            raise argparse.ArgumentTypeError(message)
        logger.info(message)

    parser2 = argparse.ArgumentParser(
        prog="bumpversion", add_help=False, parents=[parser1]
    )
    parser2.set_defaults(**defaults)

    parser2.add_argument(
        "--current-version",
        metavar="VERSION",
        help="Version that needs to be updated",
        required=False,
    )
    parser2.add_argument(
        "--parse",
        metavar="REGEX",
        help="Regex parsing the version string",
        default=defaults.get(
            "parse", r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        ),
    )
    parser2.add_argument(
        "--serialize",
        metavar="FORMAT",
        action=DiscardDefaultIfSpecifiedAppendAction,
        help="How to format what is parsed back to a version",
        default=defaults.get("serialize", [str("{major}.{minor}.{patch}")]),
    )
    parser2.add_argument(
        "--search",
        metavar="SEARCH",
        help="Template for complete string to search",
        default=defaults.get("search", "{current_version}"),
    )
    parser2.add_argument(
        "--replace",
        metavar="REPLACE",
        help="Template for complete string to replace",
        default=defaults.get("replace", "{new_version}"),
    )

    known_args, remaining_argv = parser2.parse_known_args(args)

    defaults.update(vars(known_args))

    assert isinstance(known_args.serialize, list), "Argument `serialize` must be a list"

    context = dict(
        list(time_context.items())
        + list(prefixed_environ().items())
        + list(vcs_info.items())
    )

    try:
        vc = VersionConfig(
            parse=known_args.parse,
            serialize=known_args.serialize,
            search=known_args.search,
            replace=known_args.replace,
            part_configs=part_configs,
        )
    except sre_constants.error as e:
        # TODO: use re.error here mayhaps, also: should we log?
        sys.exit(1)

    current_version = (
        vc.parse(known_args.current_version) if known_args.current_version else None
    )

    new_version = None

    if "new_version" not in defaults and known_args.current_version:
        try:
            if current_version and positionals:
                logger.info("Attempting to increment part '%s'", positionals[0])
                new_version = current_version.bump(positionals[0], vc.order())
                logger.info("Values are now: %s", keyvaluestring(new_version._values))
                defaults["new_version"] = vc.serialize(new_version, context)
        except MissingValueForSerializationException as e:
            logger.info("Opportunistic finding of new_version failed: %s", e.message)
        except IncompleteVersionRepresentationException as e:
            logger.info("Opportunistic finding of new_version failed: %s", e.message)
        except KeyError as e:
            logger.info("Opportunistic finding of new_version failed")

    parser3 = argparse.ArgumentParser(
        prog="bumpversion",
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        conflict_handler="resolve",
        parents=[parser2],
    )

    parser3.set_defaults(**defaults)

    parser3.add_argument(
        "--current-version",
        metavar="VERSION",
        help="Version that needs to be updated",
        required="current_version" not in defaults,
    )
    parser3.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        default=False,
        help="Don't write any files, just pretend.",
    )
    parser3.add_argument(
        "--new-version",
        metavar="VERSION",
        help="New version that should be in the files",
        required="new_version" not in defaults,
    )

    commitgroup = parser3.add_mutually_exclusive_group()

    commitgroup.add_argument(
        "--commit",
        action="store_true",
        dest="commit",
        help="Commit to version control",
        default=defaults.get("commit", False),
    )
    commitgroup.add_argument(
        "--no-commit",
        action="store_false",
        dest="commit",
        help="Do not commit to version control",
        default=argparse.SUPPRESS,
    )

    taggroup = parser3.add_mutually_exclusive_group()

    taggroup.add_argument(
        "--tag",
        action="store_true",
        dest="tag",
        default=defaults.get("tag", False),
        help="Create a tag in version control",
    )
    taggroup.add_argument(
        "--no-tag",
        action="store_false",
        dest="tag",
        help="Do not create a tag in version control",
        default=argparse.SUPPRESS,
    )

    signtagsgroup = parser3.add_mutually_exclusive_group()
    signtagsgroup.add_argument(
        "--sign-tags",
        action="store_true",
        dest="sign_tags",
        help="Sign tags if created",
        default=defaults.get("sign_tags", False),
    )
    signtagsgroup.add_argument(
        "--no-sign-tags",
        action="store_false",
        dest="sign_tags",
        help="Do not sign tags if created",
        default=argparse.SUPPRESS,
    )

    parser3.add_argument(
        "--tag-name",
        metavar="TAG_NAME",
        help="Tag name (only works with --tag)",
        default=defaults.get("tag_name", "v{new_version}"),
    )

    parser3.add_argument(
        "--tag-message",
        metavar="TAG_MESSAGE",
        dest="tag_message",
        help="Tag message",
        default=defaults.get(
            "tag_message", "Bump version: {current_version} → {new_version}"
        ),
    )

    parser3.add_argument(
        "--message",
        "-m",
        metavar="COMMIT_MSG",
        help="Commit message",
        default=defaults.get(
            "message", "Bump version: {current_version} → {new_version}"
        ),
    )

    file_names = []
    if "files" in defaults:
        assert defaults["files"] is not None
        file_names = defaults["files"].split(" ")

    parser3.add_argument("part", help="Part of the version to be bumped.")
    parser3.add_argument(
        "files", metavar="file", nargs="*", help="Files to change", default=file_names
    )

    args = parser3.parse_args(remaining_argv + positionals)

    if args.dry_run:
        logger.info("Dry run active, won't touch any files.")

    if args.new_version:
        new_version = vc.parse(args.new_version)

    logger.info("New version will be '%s'", args.new_version)

    file_names = file_names or positionals[1:]

    for file_name in file_names:
        files.append(ConfiguredFile(file_name, vc))

    for vcs in VCS:
        if vcs.is_usable():
            try:
                vcs.assert_nondirty()
            except WorkingDirectoryIsDirtyException as e:
                if not defaults["allow_dirty"]:
                    logger.warning(
                        "%s\n\nUse --allow-dirty to override this if you know what you're doing.",
                        e.message
                    )
                    raise
            break
        else:
            vcs = None

    # make sure files exist and contain version string

    logger.info(
        "Asserting files %s contain the version string...",
        ", ".join([str(f) for f in files])
    )

    for f in files:
        f.should_contain_version(current_version, context)

    # change version string in files
    for f in files:
        f.replace(current_version, new_version, context, args.dry_run)

    commit_files = [f.path for f in files]

    config.set("bumpversion", "new_version", args.new_version)

    for key, value in config.items("bumpversion"):
        logger_list.info("%s=%s", key, value)

    config.remove_option("bumpversion", "new_version")

    config.set("bumpversion", "current_version", args.new_version)

    new_config = StringIO()

    try:
        write_to_config_file = (not args.dry_run) and config_file_exists

        logger.info(
            "%s to config file %s:",
            "Would write" if not write_to_config_file else "Writing",
            config_file
        )

        config.write(new_config)
        logger.info(new_config.getvalue())

        if write_to_config_file:
            with io.open(config_file, "wt", encoding="utf-8", newline=config_new_lines) as f:
                f.write(new_config.getvalue().strip()+'\n')

    except UnicodeEncodeError:
        warnings.warn(
            "Unable to write UTF-8 to config file, because of an old configparser version. "
            "Update with `pip install --upgrade configparser`."
        )

    if config_file_exists:
        commit_files.append(config_file)

    if not vcs:
        return

    assert vcs.is_usable(), "Did find '{}' unusable, unable to commit.".format(
        vcs.__name__
    )

    do_commit = args.commit and not args.dry_run
    do_tag = args.tag and not args.dry_run

    logger.info(
        "%s %s commit",
        "Would prepare" if not do_commit else "Preparing",
        vcs.__name__,
    )

    for path in commit_files:
        logger.info(
            "%s changes in file '%s' to %s",
            "Would add" if not do_commit else "Adding",
            path,
            vcs.__name__,
        )

        if do_commit:
            vcs.add_path(path)

    vcs_context = {
        "current_version": args.current_version,
        "new_version": args.new_version,
    }
    vcs_context.update(time_context)
    vcs_context.update(prefixed_environ())

    commit_message = args.message.format(**vcs_context)

    logger.info(
        "%s to %s with message '%s'",
        "Would commit" if not do_commit else "Committing",
        vcs.__name__,
        commit_message,
    )

    if do_commit:
        vcs.commit(message=commit_message)

    sign_tags = args.sign_tags
    tag_name = args.tag_name.format(**vcs_context)
    tag_message = args.tag_message.format(**vcs_context)
    logger.info(
        "%s '%s' %s in %s and %s",
        "Would tag" if not do_tag else "Tagging",
        tag_name,
        "with message '{}'".format(tag_message) if tag_message else "without message",
        vcs.__name__,
        "signing" if sign_tags else "not signing",
    )

    if do_tag:
        vcs.tag(sign_tags, tag_name, tag_message)
