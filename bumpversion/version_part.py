import logging
import re
import sre_constants
import string

from bumpversion.exceptions import (
    MissingValueForSerializationException,
    IncompleteVersionRepresentationException,
    InvalidVersionPartException,
)
from bumpversion.functions import NumericFunction, ValuesFunction
from bumpversion.utils import keyvaluestring


logger = logging.getLogger(__name__)


class PartConfiguration:

    function_cls = NumericFunction

    def __init__(self, *args, **kwds):
        self.function = self.function_cls(*args, **kwds)

    @property
    def first_value(self):
        return str(self.function.first_value)

    @property
    def optional_value(self):
        return str(self.function.optional_value)

    @property
    def independent(self):
        return self.function.independent

    def bump(self, value=None):
        return self.function.bump(value)


class ConfiguredVersionPartConfiguration(PartConfiguration):

    function_cls = ValuesFunction


class NumericVersionPartConfiguration(PartConfiguration):

    function_cls = NumericFunction


class VersionPart:
    """
    Represent part of a version number.

    Offer a self.config object that rules how the part behaves when
    increased or reset.
    """

    def __init__(self, value, config=None):
        self._value = value

        if config is None:
            config = NumericVersionPartConfiguration()

        self.config = config

    @property
    def value(self):
        return self._value or self.config.optional_value

    def copy(self):
        return VersionPart(self._value)

    def bump(self):
        return VersionPart(self.config.bump(self.value), self.config)

    def is_optional(self):
        return self.value == self.config.optional_value

    def is_independent(self):
        return self.config.independent

    def __format__(self, format_spec):
        return self.value

    def __repr__(self):
        return "<bumpversion.VersionPart:{}:{}>".format(
            self.config.__class__.__name__, self.value
        )

    def __eq__(self, other):
        return self.value == other.value

    def null(self):
        return VersionPart(self.config.first_value, self.config)


class Version:

    def __init__(self, values, original=None):
        self._values = dict(values)
        self.original = original

    def __getitem__(self, key):
        return self._values[key]

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return "<bumpversion.Version:{}>".format(keyvaluestring(self._values))

    def bump(self, part_name, order):
        bumped = False

        new_values = {}

        for label in order:
            if label not in self._values:
                continue
            if label == part_name:
                new_values[label] = self._values[label].bump()
                bumped = True
            elif bumped and not self._values[label].is_independent():
                new_values[label] = self._values[label].null()
            else:
                new_values[label] = self._values[label].copy()

        if not bumped:
            raise InvalidVersionPartException("No part named %r" % part_name)

        new_version = Version(new_values)

        return new_version


def labels_for_format(serialize_format):
    return (
        label for _, label, _, _ in string.Formatter().parse(serialize_format) if label
    )


class VersionConfig:
    """
    Hold a complete representation of a version string.
    """

    def __init__(self, parse, serialize, search, replace, part_configs=None):
        try:
            self.parse_regex = re.compile(parse, re.VERBOSE)
        except sre_constants.error as e:
            # TODO: use re.error here mayhaps
            logger.error("--parse '%s' is not a valid regex", parse)
            raise e

        self.serialize_formats = serialize

        if not part_configs:
            part_configs = {}

        self.part_configs = part_configs
        self.search = search
        self.replace = replace

    def order(self):
        # currently, order depends on the first given serialization format
        # this seems like a good idea because this should be the most complete format
        return labels_for_format(self.serialize_formats[0])

    def parse(self, version_string):
        if not version_string:
            return None

        regexp_one_line = "".join(
            [l.split("#")[0].strip() for l in self.parse_regex.pattern.splitlines()]
        )

        logger.info(
            "Parsing version '%s' using regexp '%s'",
            version_string,
            regexp_one_line,
        )

        match = self.parse_regex.search(version_string)

        _parsed = {}
        if not match:
            logger.warning(
                "Evaluating 'parse' option: '%s' does not parse current version '%s'",
                self.parse_regex.pattern,
                version_string,
            )
            return None

        for key, value in match.groupdict().items():
            _parsed[key] = VersionPart(value, self.part_configs.get(key))

        v = Version(_parsed, version_string)

        logger.info("Parsed the following values: %s", keyvaluestring(v._values))

        return v

    def _serialize(self, version, serialize_format, context, raise_if_incomplete=False):
        """
        Attempts to serialize a version with the given serialization format.

        Raises MissingValueForSerializationException if not serializable
        """
        values = context.copy()
        for k in version:
            values[k] = version[k]

        # TODO dump complete context on debug level

        try:
            # test whether all parts required in the format have values
            serialized = serialize_format.format(**values)

        except KeyError as e:
            missing_key = getattr(e, "message", e.args[0])
            raise MissingValueForSerializationException(
                "Did not find key {} in {} when serializing version number".format(
                    repr(missing_key), repr(version)
                )
            )

        keys_needing_representation = set()

        keys = list(self.order())
        for i, k in enumerate(keys):
            v = values[k]

            if not isinstance(v, VersionPart):
                # values coming from environment variables don't need
                # representation
                continue

            if not v.is_optional():
                keys_needing_representation = set(keys[:i+1])

        required_by_format = set(labels_for_format(serialize_format))

        # try whether all parsed keys are represented
        if raise_if_incomplete:
            if not keys_needing_representation <= required_by_format:
                raise IncompleteVersionRepresentationException(
                    "Could not represent '{}' in format '{}'".format(
                        "', '".join(keys_needing_representation ^ required_by_format),
                        serialize_format,
                    )
                )

        return serialized

    def _choose_serialize_format(self, version, context):
        chosen = None

        logger.debug("Available serialization formats: '%s'", "', '".join(self.serialize_formats))

        for serialize_format in self.serialize_formats:
            try:
                self._serialize(
                    version, serialize_format, context, raise_if_incomplete=True
                )
                # Prefer shorter or first search expression.
                chosen_part_count = None if not chosen else len(list(string.Formatter().parse(chosen)))
                serialize_part_count = len(list(string.Formatter().parse(serialize_format)))
                if not chosen or chosen_part_count > serialize_part_count:
                    chosen = serialize_format
                    logger.debug("Found '%s' to be a usable serialization format", chosen)
                else:
                    logger.debug("Found '%s' usable serialization format, but it's longer", serialize_format)
            except IncompleteVersionRepresentationException as e:
                # If chosen, prefer shorter
                if not chosen:
                    chosen = serialize_format
            except MissingValueForSerializationException as e:
                logger.info(e.message)
                raise e

        if not chosen:
            raise KeyError("Did not find suitable serialization format")

        logger.debug("Selected serialization format '%s'", chosen)

        return chosen

    def serialize(self, version, context):
        serialized = self._serialize(
            version, self._choose_serialize_format(version, context), context
        )
        logger.debug("Serialized to '%s'", serialized)
        return serialized
