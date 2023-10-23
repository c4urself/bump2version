import pytest

from bumpversion.version_part import (
    ConfiguredVersionPartConfiguration,
    NumericVersionPartConfiguration,
    VersionPart,
    VersionConfig,
)


@pytest.fixture(params=[None, (('0', '1', '2'),), (('0', '3'),)])
def confvpc(request):
    """Return a three-part and a two-part version part configuration."""
    if request.param is None:
        return NumericVersionPartConfiguration()
    else:
        return ConfiguredVersionPartConfiguration(*request.param)


# VersionPart

def test_version_part_init(confvpc):
    assert VersionPart(
        confvpc.first_value, confvpc).value == confvpc.first_value


def test_version_part_copy(confvpc):
    vp = VersionPart(confvpc.first_value, confvpc)
    vc = vp.copy()
    assert vp.value == vc.value
    assert id(vp) != id(vc)


def test_version_part_bump(confvpc):
    vp = VersionPart(confvpc.first_value, confvpc)
    vc = vp.bump()
    assert vc.value == confvpc.bump(confvpc.first_value)


def test_bump_resets_lower_parts_to_default_value():
    # See bug 134.
    release_part_config = ConfiguredVersionPartConfiguration(
        first_value="dev",
        optional_value="prod",
        values=["dev", "prod"],
    )
    version_config = VersionConfig(
        parse=r"(?P<major>\d+)(\-(?P<release>[a-z]+)(?P<build>\d+))?",
        serialize=["{major}-{release}{build}", "{major}"],
        part_configs={"release": release_part_config},
        search=None,
        replace=None,
    )

    # Start with version "0", mapping to "0-prod0".
    # Bump `build` from 0 to 1.
    # Part `release` should remain `prod` and be serialized as such.
    version = version_config.parse("0")
    new_version = version.bump("build", version_config.order())
    assert version_config.serialize(new_version) == "0-prod1"


def test_version_part_check_optional_false(confvpc):
    assert not VersionPart(confvpc.first_value, confvpc).bump().is_optional()


def test_version_part_check_optional_true(confvpc):
    assert VersionPart(confvpc.first_value, confvpc).is_optional()


def test_version_part_format(confvpc):
    assert "{}".format(
        VersionPart(confvpc.first_value, confvpc)) == confvpc.first_value


def test_version_part_equality(confvpc):
    assert VersionPart(confvpc.first_value, confvpc) == VersionPart(
        confvpc.first_value, confvpc)


def test_version_part_null(confvpc):
    assert VersionPart(confvpc.first_value, confvpc).null() == VersionPart(
        confvpc.first_value, confvpc)
