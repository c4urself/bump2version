from bumpversion.functions import NumericFunction, ValuesFunction

class PartConfiguration(object):
    function_cls = NumericFunction

    def __init__(self, *args, **kwds):
        self.function = self.function_cls(*args, **kwds)

    @property
    def first_value(self):
        return str(self.function.first_value)

    @property
    def optional_value(self):
        return str(self.function.optional_value)

    def bump(self, value=None):
        return self.function.bump(value)


class ConfiguredVersionPartConfiguration(PartConfiguration):
    function_cls = ValuesFunction


class NumericVersionPartConfiguration(PartConfiguration):
    function_cls = NumericFunction


class VersionPart(object):

    """
    This class represents part of a version number. It contains a self.config
    object that rules how the part behaves when increased or reset.
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

    def __format__(self, format_spec):
        return self.value

    def __repr__(self):
        return '<bumpversion.VersionPart:{}:{}>'.format(
            self.config.__class__.__name__,
            self.value
        )

    def __hash__(self):
        return hash(self.value)

    def _compare(self, other, method):
        if self.config.function_cls is not other.config.function_cls:
            raise TypeError("Versions use different part specific configuration, cant compare them.")
        if self.config.function_cls is NumericFunction:
            return method(self.value, other.value)
        else:
            # Compare order
            idx1 = self.config.function.index(self.value)
            idx2 = other.config.function.index(other.value)
            return method(idx1, idx2)

    def __eq__(self, other):
        return self._compare(other, lambda s, o: s == o)

    def __lt__(self, other):
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s, o: s <= o)

    def __ge__(self, other):
        return self._compare(other, lambda s, o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s, o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s, o: s != o)

    def null(self):
        return VersionPart(self.config.first_value, self.config)
