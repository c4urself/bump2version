from argparse import _AppendAction
from difflib import unified_diff
import io
import logging
import os

from bumpversion.exceptions import VersionNotFoundException, SearchRegexException
import re

logger = logging.getLogger("bumpversion.cli")


class DiscardDefaultIfSpecifiedAppendAction(_AppendAction):

    """
    Fixes bug http://bugs.python.org/issue16399 for 'append' action
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(self, "_discarded_default", None) is None:
            setattr(namespace, self.dest, [])
            self._discarded_default = True  # pylint: disable=attribute-defined-outside-init

        super().__call__(
            parser, namespace, values, option_string=None
        )


def keyvaluestring(d):
    return ", ".join("{}={}".format(k, v) for k, v in sorted(d.items()))


def prefixed_environ():
    return {"${}".format(key): value for key, value in os.environ.items()}


class ConfiguredFile:

    def __init__(self, path, versionconfig):
        self.path = path
        self._versionconfig = versionconfig

    def should_contain_version(self, version, context):
        """
        Raise VersionNotFound if the version number isn't present in this file.

        Return normally if the version number is in fact present.
        """
        context["current_version"] = self._versionconfig.serialize(version, context)

        if not self._versionconfig.search_regex:
            search_expression = self._versionconfig.search.format(**context)

            if self.contains(search_expression):
                return

            # the `search` pattern did not match, but the original supplied
            # version number (representing the same version part values) might
            # match instead.

            # check whether `search` isn't customized, i.e. should match only
            # very specific parts of the file
            search_pattern_is_default = self._versionconfig.search == "{current_version}"

            if search_pattern_is_default and self.contains(version.original):
                # original version is present and we're not looking for something
                # more specific -> this is accepted as a match
                return

            # version not found
            raise VersionNotFoundException(
                "Did not find '{}' in file: '{}'".format(
                    search_expression, self.path
                )
            )
        else:
            regex = self._escape_regex_braces(self._versionconfig.search_regex)
            context["current_version"] = re.escape(context["current_version"])
            search_expression = regex.format(**context)

            try:
                if self.contains(search_expression, regex=True):
                    return
            except re.error as error:
                raise SearchRegexException("Search regex error: {}".format(error))

            # version not found
            raise VersionNotFoundException(
                "Did not match '{}' in file: '{}'".format(
                    search_expression, self.path
                )
            )

    def _escape_regex_braces(self, regex):
        # Escape regex braces to support current_version template string
        regex = re.sub(r"\{(?!current_version)", "{{", regex)
        regex = re.sub(r"(?<!current_version)\}", "}}", regex)
        return regex

    def contains(self, search, regex=False):
        found_or_match = False

        if not search:
            return False

        if not regex:
            with open(self.path, "rt", encoding="utf-8") as f:
                search_lines = search.splitlines()
                lookbehind = []

                for lineno, line in enumerate(f.readlines()):
                    lookbehind.append(line.rstrip("\n"))

                    if len(lookbehind) > len(search_lines):
                        lookbehind = lookbehind[1:]

                    if (
                        search_lines[0] in lookbehind[0]
                        and search_lines[-1] in lookbehind[-1]
                        and search_lines[1:-1] == lookbehind[1:-1]
                    ):
                        logger.info(
                            "Found '%s' in %s at line %s:\n%s",
                            search,
                            self.path,
                            lineno - (len(lookbehind) - 2),
                            line.rstrip(),
                        )
                        found_or_match = True
        else:
            with open(self.path, "rt", encoding="utf-8") as f:
                file_content = f.read()
                look_around = 100
                matches = re.compile(search, re.MULTILINE|re.DOTALL)
                for match in matches.finditer(file_content):
                    lineno, line = file_content[0:match.start()].count("\n"), file_content[(match.start()-look_around):(match.end()+look_around)]
                    line = "\n".join(line.split("\n")[1:-1]) if len(line.split("\n")) >= 3 else line
                    logger.info(
                        "Matched '%s' in %s at line %s:\n%s",
                        search,
                        self.path,
                        (lineno + 1),
                        line.rstrip(),
                    )
                    found_or_match = True

        return found_or_match

    def replace(self, current_version, new_version, context, dry_run):

        with open(self.path, "rt", encoding="utf-8") as f:
            file_content_before = f.read()
            file_new_lines = f.newlines

        context["current_version"] = self._versionconfig.serialize(
            current_version, context
        )
        context["new_version"] = self._versionconfig.serialize(new_version, context)

        search_for = self._versionconfig.search.format(**context)
        search_for_regex = self._versionconfig.search_regex
        if search_for_regex:
            regex = self._escape_regex_braces(self._versionconfig.search_regex)
            context["current_version"] = re.escape(context["current_version"])
            search_for_regex = regex.format(**context)
        replace_with = self._versionconfig.replace.format(**context)

        file_content_after = file_content_before.replace(search_for, replace_with)

        try:
            file_content_after = re.sub(search_for_regex, replace_with, file_content_before) if search_for_regex else file_content_before.replace(search_for, replace_with)
        except re.error as error:
            raise SearchRegexException("Search regex error: {}".format(error))

        if not search_for_regex and file_content_before == file_content_after:
            # TODO expose this to be configurable
            file_content_after = file_content_before.replace(
                current_version.original, replace_with
            )

        if file_content_before != file_content_after:
            logger.info("%s file %s:", "Would change" if dry_run else "Changing", self.path)
            logger.info(
                "\n".join(
                    list(
                        unified_diff(
                            file_content_before.splitlines(),
                            file_content_after.splitlines(),
                            lineterm="",
                            fromfile="a/" + self.path,
                            tofile="b/" + self.path,
                        )
                    )
                )
            )
        else:
            logger.info("%s file %s", "Would not change" if dry_run else "Not changing", self.path)

        if not dry_run:
            with open(self.path, "wt", encoding="utf-8", newline=file_new_lines) as f:
                f.write(file_content_after)

    def __str__(self):
        return self.path

    def __repr__(self):
        return "<bumpversion.ConfiguredFile:{}>".format(self.path)
