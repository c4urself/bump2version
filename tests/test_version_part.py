import pytest
from unittest import mock

from bumpversion.version_part import (
    ConfiguredVersionPartConfiguration,
    NumericVersionPartConfiguration,
    VersionPart,
    VersionConfig,
    Version,
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
    vc = vp.bump()[0]
    assert vc.value == confvpc.bump(confvpc.first_value)[0]


def test_version_part_check_optional_false(confvpc):
    assert not VersionPart(confvpc.first_value, confvpc).bump()[0].is_optional()


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


# Conditional bumping

def bump_patch(version: Version):
    if version["release"].value != "gamma":
        version["release"].value = "gamma"
        return ["release"]
    return []


@pytest.fixture
@mock.patch("bumpversion.functions._get_function_from_path")
def version_config(mock_conditional):
    mock_conditional.return_value = bump_patch

    release_part_config = ConfiguredVersionPartConfiguration(
        first_value="beta",
        optional_value="gamma",
        values=["beta", "gamma"],
    )
    patch_part_config = NumericVersionPartConfiguration(
        first_value="1",
        conditional_bump="my.function"
    )
    version_config = VersionConfig(
        parse=r"(?P<major>\d+)\.(?P<patch>\d+)(\-(?P<release>[a-z]+))?",
        serialize=["{major}.{patch}-{release}", "{major}.{patch}"],
        part_configs={
            "release": release_part_config,
            "patch": patch_part_config,
        },
        search=None,
        replace=None,
    )
    return version_config


def test_version_conditional_bump_optional_value(version_config):
    version = version_config.parse("2.4-beta")
    new_version = version.bump("patch", version_config.order())
    assert version_config.serialize(new_version, {}) == "2.5"


def test_version_conditional_bump_required_value(version_config):
    version_config.part_configs["release"].function.optional_value = None

    version = version_config.parse("2.4-beta")
    new_version = version.bump("patch", version_config.order())
    assert version_config.serialize(new_version, {}) == "2.5-gamma"

