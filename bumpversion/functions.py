import re
from importlib import import_module


class NumericFunction:

    """
    This is a class that provides a numeric function for version parts.
    It simply starts with the provided first_value (0 by default) and
    increases it following the sequence of integer numbers.

    The optional value of this function is equal to the first value.

    This function also supports alphanumeric parts, altering just the numeric
    part (e.g. 'r3' --> 'r4'). Only the first numeric group found in the part is
    considered (e.g. 'r3-001' --> 'r4-001').
    """

    FIRST_NUMERIC = re.compile(r"([^\d]*)(\d+)(.*)")

    def __init__(self, first_value=None, side_effect=None):

        if first_value is not None:
            try:
                _, _, _ = self.FIRST_NUMERIC.search(
                    first_value
                ).groups()
            except AttributeError:
                raise ValueError(
                    "The given first value {} does not contain any digit".format(first_value)
                )
        else:
            first_value = 0

        self.first_value = str(first_value)
        self.optional_value = self.first_value
        self.side_effect = _get_side_effect_function(side_effect)

    def bump(self, value, version=None, part_key=None):
        part_prefix, part_numeric, part_suffix = self.FIRST_NUMERIC.search(
            value
        ).groups()

        _execute_side_effect(self.side_effect, version)
        bumped_numeric = _get_next_part_value(part_key, version, int(part_numeric) + 1)

        return "".join([part_prefix, str(bumped_numeric), part_suffix])


def _get_side_effect_function(path: str):
    if path is not None:
        # Path could be `something.module.function`, we want just `something.module`
        # and then get just `function`.
        module_path = ".".join(path.split(".")[:-1])
        function_name = path.split(".")[-1]
        module = import_module(module_path)
        return getattr(module, function_name)


def _execute_side_effect(side_effect=None, version=None):
    if side_effect is not None:
        side_effect(version)


def _get_next_part_value(part_key, version, standard_value):
    """
    If the part was not manually set then it returns the `standard_value`.
    Otherwise it will return the manually set value for the target part.
    The part may be manually set within a user's side_effect function if they have one.
    """
    if part_key is not None and version[part_key].manually_set:
        return version[part_key].value
    return standard_value


class ValuesFunction:

    """
    This is a class that provides a values list based function for version parts.
    It is initialized with a list of values and iterates through them when
    bumping the part.

    The default optional value of this function is equal to the first value,
    but may be otherwise specified.

    When trying to bump a part which has already the maximum value in the list
    you get a ValueError exception.
    """

    def __init__(self, values, optional_value=None, first_value=None, side_effect=None):

        if not values:
            raise ValueError("Version part values cannot be empty")

        self._values = values

        if optional_value is None:
            optional_value = values[0]

        if optional_value not in values:
            raise ValueError(
                "Optional value {} must be included in values {}".format(
                    optional_value, values
                )
            )

        self.optional_value = optional_value

        if first_value is None:
            first_value = values[0]

        if first_value not in values:
            raise ValueError(
                "First value {} must be included in values {}".format(
                    first_value, values
                )
            )

        self.first_value = first_value
        self.side_effect = _get_side_effect_function(side_effect)
        self.part_key = None

    def bump(self, value, version=None, part_key=None):
        try:
            _execute_side_effect(self.side_effect, version)
            bumped_value = _get_next_part_value(
                part_key, version, self._values[self._values.index(value) + 1]
            )

            return bumped_value
        except IndexError:
            raise ValueError(
                "The part has already the maximum value among {} and cannot be bumped.".format(
                    self._values
                )
            )
