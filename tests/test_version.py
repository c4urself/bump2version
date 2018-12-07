# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import pytest

from bumpversion import VersionConfig
from bumpversion.version_part import ConfiguredVersionPartConfiguration


def test_compare_versions_numeric():

    version_parse = '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'
    version_serialize = [str('{major}.{minor}.{patch}')]
    vc = VersionConfig(version_parse, version_serialize, None, None)
    v1 = vc.parse(version_string="1.0.0")
    v2 = vc.parse(version_string="1.0.0")
    assert v1 == v2
    assert not (v1 != v2)
    assert not (v1 < v2)
    assert not (v1 > v2)
    assert v1 <= v2
    assert v1 >= v2
    assert v2 == v1
    assert not (v2 != v1)
    assert not (v2 < v1)
    assert not (v2 > v1)
    assert v2 <= v1
    assert v2 >= v1
    v2 = vc.parse(version_string="1.0.1")
    assert not (v1 == v2)
    assert v1 != v2
    assert v1 < v2
    assert not (v1 > v2)
    assert v1 <= v2
    assert not (v1 >= v2)
    assert not (v2 == v1)
    assert v2 != v1
    assert not (v2 < v1)
    assert v2 > v1
    assert not (v2 <= v1)
    assert v2 >= v1
    v1 = vc.parse(version_string="1.2.1")
    v2 = vc.parse(version_string="1.3.1")
    assert not (v1 == v2)
    assert v1 != v2
    assert v1 < v2
    assert not (v1 > v2)
    assert v1 <= v2
    assert not (v1 >= v2)
    assert not (v2 == v1)
    assert v2 != v1
    assert not (v2 < v1)
    assert v2 > v1
    assert not (v2 <= v1)
    assert v2 >= v1
    v1 = vc.parse(version_string="1.2.4")
    v2 = vc.parse(version_string="1.3.1")
    assert not (v1 == v2)
    assert v1 != v2
    assert v1 < v2
    assert not (v1 > v2)
    assert v1 <= v2
    assert not (v1 >= v2)
    assert not (v2 == v1)
    assert v2 != v1
    assert not (v2 < v1)
    assert v2 > v1
    assert not (v2 <= v1)
    assert v2 >= v1
    v1 = vc.parse(version_string="1.2.4")
    v2 = vc.parse(version_string="2.3.1")
    assert not (v1 == v2)
    assert v1 != v2
    assert v1 < v2
    assert not (v1 > v2)
    assert v1 <= v2
    assert not (v1 >= v2)
    assert not (v2 == v1)
    assert v2 != v1
    assert not (v2 < v1)
    assert v2 > v1
    assert not (v2 <= v1)
    assert v2 >= v1
    v1 = vc.parse(version_string="3.2.4")
    v2 = vc.parse(version_string="2.3.1")
    assert not (v1 == v2)
    assert v1 != v2
    assert not (v1 < v2)
    assert v1 > v2
    assert not (v1 <= v2)
    assert v1 >= v2
    assert not (v2 == v1)
    assert v2 != v1
    assert v2 < v1
    assert not (v2 > v1)
    assert v2 <= v1
    assert not (v2 >= v1)


def test_compare_versions_values():

    version_parse = '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<release>.+)'
    version_serialize = [str('{major}.{minor}.{release}')]
    pc = ConfiguredVersionPartConfiguration(values=['witty-warthog', 'ridiculous-rat', 'marvelous-mantis'])
    part_configs = {'release': pc}
    vc = VersionConfig(version_parse, version_serialize, None, None, part_configs=part_configs)
    v1 = vc.parse(version_string="1.0.witty-warthog")
    v2 = vc.parse(version_string="1.0.witty-warthog")
    assert v1 == v2
    assert not (v1 != v2)
    assert not (v1 < v2)
    assert not (v1 > v2)
    assert v1 <= v2
    assert v1 >= v2
    assert v2 == v1
    assert not (v2 != v1)
    assert not (v2 < v1)
    assert not (v2 > v1)
    assert v2 <= v1
    assert v2 >= v1
    v2 = vc.parse(version_string="1.0.ridiculous-rat")
    assert not (v1 == v2)
    assert v1 != v2
    assert v1 < v2
    assert not (v1 > v2)
    assert v1 <= v2
    assert not (v1 >= v2)
    assert not (v2 == v1)
    assert v2 != v1
    assert not (v2 < v1)
    assert v2 > v1
    assert not (v2 <= v1)
    assert v2 >= v1
    v1 = vc.parse(version_string="1.2.marvelous-mantis")
    v2 = vc.parse(version_string="1.3.ridiculous-rat")
    assert not (v1 == v2)
    assert v1 != v2
    assert v1 < v2
    assert not (v1 > v2)
    assert v1 <= v2
    assert not (v1 >= v2)
    assert not (v2 == v1)
    assert v2 != v1
    assert not (v2 < v1)
    assert v2 > v1
    assert not (v2 <= v1)
    assert v2 >= v1