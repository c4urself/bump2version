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

    def __init__(self, first_value=None, conditional_bump=None):

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
        self.conditional_bump = _get_function_from_path(conditional_bump)

    def bump(self, value, version=None):
        part_prefix, part_numeric, part_suffix = self.FIRST_NUMERIC.search(
            value
        ).groups()

        bumped_numeric = int(part_numeric) + 1
        parts_conditionally_bumped = _execute_conditional_bump(self.conditional_bump, version)

        return (
            "".join([part_prefix, str(bumped_numeric), part_suffix]),
            parts_conditionally_bumped
        )


def _get_function_from_path(path: str):
    if path is not None:
        # Path could be `something.module.function`, we want just `something.module`
        # and then get just `function`.
        module_path = "".join(path.split(".")[:-1])
        function_name = path.split(".")[-1]
        module = import_module(module_path)
        return getattr(module, function_name)


def _execute_conditional_bump(conditional_bump=None, version=None):
    if conditional_bump is not None:
        return conditional_bump(version)
    return []


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

    def __init__(self, values, optional_value=None, first_value=None, conditional_bump=None):

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
        self.conditional_bump = conditional_bump

    def bump(self, value, version=None):
        try:
            parts_conditionally_bumped = _execute_conditional_bump(self.conditional_bump, version)
            return (
                self._values[self._values.index(value) + 1],
                parts_conditionally_bumped
            )
        except IndexError:
            raise ValueError(
                "The part has already the maximum value among {} and cannot be bumped.".format(
                    self._values
                )
            )
