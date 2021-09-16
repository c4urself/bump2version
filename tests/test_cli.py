import argparse
import logging
import os
import platform
import warnings
import subprocess
from configparser import RawConfigParser
from datetime import datetime
from functools import partial
from shlex import split as shlex_split
from textwrap import dedent
from unittest import mock

import pytest
from testfixtures import LogCapture

import bumpversion
from bumpversion import exceptions
from bumpversion.cli import DESCRIPTION, main, split_args_in_optional_and_positional


def _get_subprocess_env():
    env = os.environ.copy()
    env['HGENCODING'] = 'utf-8'
    return env


SUBPROCESS_ENV = _get_subprocess_env()
call = partial(subprocess.call, env=SUBPROCESS_ENV, shell=True)
check_call = partial(subprocess.check_call, env=SUBPROCESS_ENV)
check_output = partial(subprocess.check_output,  env=SUBPROCESS_ENV)
run = partial(subprocess.run, env=SUBPROCESS_ENV)

xfail_if_no_git = pytest.mark.xfail(
  call("git version") != 0,
  reason="git is not installed"
)

xfail_if_no_hg = pytest.mark.xfail(
  call("hg version") != 0,
  reason="hg is not installed"
)

VCS_GIT = pytest.param("git", marks=xfail_if_no_git())
VCS_MERCURIAL = pytest.param("hg", marks=xfail_if_no_hg())
COMMIT = "[bumpversion]\ncommit = True"
COMMIT_NOT_TAG = "[bumpversion]\ncommit = True\ntag = False"


@pytest.fixture(params=[VCS_GIT, VCS_MERCURIAL])
def vcs(request):
    """Return all supported VCS systems (git, hg)."""
    return request.param


@pytest.fixture(params=[VCS_GIT])
def git(request):
    """Return git as VCS (not hg)."""
    return request.param


@pytest.fixture(params=['.bumpversion.cfg', 'setup.cfg'])
def configfile(request):
    """Return both config-file styles ('.bumpversion.cfg', 'setup.cfg')."""
    return request.param


@pytest.fixture(params=[
    "file",
    "file(suffix)",
    "file (suffix with space)",
    "file (suffix lacking closing paren",
])
def file_keyword(request):
    """Return multiple possible styles for the bumpversion:file keyword."""
    return request.param


try:
    RawConfigParser(empty_lines_in_values=False)
    using_old_configparser = False
except TypeError:
    using_old_configparser = True

xfail_if_old_configparser = pytest.mark.xfail(
  using_old_configparser,
  reason="configparser doesn't support empty_lines_in_values"
)


def _mock_calls_to_string(called_mock):
    return ["{}|{}|{}".format(
        name,
        args[0] if len(args) > 0 else args,
        repr(kwargs) if len(kwargs) > 0 else ""
    ) for name, args, kwargs in called_mock.mock_calls]


EXPECTED_OPTIONS = r"""
[-h]
[--config-file FILE]
[--verbose]
[--list]
[--allow-dirty]
[--parse REGEX]
[--serialize FORMAT]
[--search SEARCH]
[--replace REPLACE]
[--current-version VERSION]
[--no-configured-files]
[--dry-run]
--new-version VERSION
[--commit | --no-commit]
[--tag | --no-tag]
[--sign-tags | --no-sign-tags]
[--tag-name TAG_NAME]
[--tag-message TAG_MESSAGE]
[--message COMMIT_MSG]
part
[file [file ...]]
""".strip().splitlines()

EXPECTED_USAGE = (r"""

%s

positional arguments:
  part                  Part of the version to be bumped.
  file                  Files to change (default: [])

optional arguments:
  -h, --help            show this help message and exit
  --config-file FILE    Config file to read most of the variables from
                        (default: .bumpversion.cfg)
  --verbose             Print verbose logging to stderr (default: 0)
  --list                List machine readable information (default: False)
  --allow-dirty         Don't abort if working directory is dirty (default:
                        False)
  --parse REGEX         Regex parsing the version string (default:
                        (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))
  --serialize FORMAT    How to format what is parsed back to a version
                        (default: ['{major}.{minor}.{patch}'])
  --search SEARCH       Template for complete string to search (default:
                        {current_version})
  --replace REPLACE     Template for complete string to replace (default:
                        {new_version})
  --current-version VERSION
                        Version that needs to be updated (default: None)
  --no-configured-files
                        Only replace the version in files specified on the
                        command line, ignoring the files from the
                        configuration file. (default: False)
  --dry-run, -n         Don't write any files, just pretend. (default: False)
  --new-version VERSION
                        New version that should be in the files (default:
                        None)
  --commit              Commit to version control (default: False)
  --no-commit           Do not commit to version control
  --tag                 Create a tag in version control (default: False)
  --no-tag              Do not create a tag in version control
  --sign-tags           Sign tags if created (default: False)
  --no-sign-tags        Do not sign tags if created
  --tag-name TAG_NAME   Tag name (only works with --tag) (default:
                        v{new_version})
  --tag-message TAG_MESSAGE
                        Tag message (default: Bump version: {current_version}
                        → {new_version})
  --message COMMIT_MSG, -m COMMIT_MSG
                        Commit message (default: Bump version:
                        {current_version} → {new_version})
""" % DESCRIPTION).lstrip()


def test_usage_string(tmpdir, capsys):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()
    assert err == ""

    for option_line in EXPECTED_OPTIONS:
        assert option_line in out, "Usage string is missing {}".format(option_line)

    assert EXPECTED_USAGE in out


def test_usage_string_fork(tmpdir):
    tmpdir.chdir()

    if platform.system() == "Windows":
        # There are encoding problems on Windows with the encoding of →
        tmpdir.join(".bumpversion.cfg").write(dedent("""
             [bumpversion]
             message: Bump version: {current_version} to {new_version}
             tag_message: 'Bump version: {current_version} to {new_version}
             """))

    try:
        out = check_output('bumpversion --help', shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        out = e.output

    if b'usage: bumpversion [-h]' not in out:
        print(out)

    assert b'usage: bumpversion [-h]' in out


def test_regression_help_in_work_dir(tmpdir, capsys, vcs):
    tmpdir.chdir()
    tmpdir.join("some_source.txt").write("1.7.2013")
    check_call([vcs, "init"])
    check_call([vcs, "add", "some_source.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])
    check_call([vcs, "tag", "v1.7.2013"])

    with pytest.raises(SystemExit):
        main(['--help'])

    out, err = capsys.readouterr()

    for option_line in EXPECTED_OPTIONS:
        assert option_line in out, "Usage string is missing {}".format(option_line)

    if vcs == "git":
        assert "Version that needs to be updated (default: 1.7.2013)" in out
    else:
        assert EXPECTED_USAGE in out


def test_defaults_in_usage_with_config(tmpdir, capsys):
    tmpdir.chdir()
    tmpdir.join("my_defaults.cfg").write("""[bumpversion]
current_version: 18
new_version: 19
[bumpversion:file:file1]
[bumpversion:file:file2]
[bumpversion:file:file3]""")
    with pytest.raises(SystemExit):
        main(['--config-file', 'my_defaults.cfg', '--help'])

    out, err = capsys.readouterr()

    assert "Version that needs to be updated (default: 18)" in out
    assert "New version that should be in the files (default: 19)" in out
    assert "[--current-version VERSION]" in out
    assert "[--new-version VERSION]" in out
    assert "[file [file ...]]" in out


def test_missing_explicit_config_file(tmpdir):
    tmpdir.chdir()
    with pytest.raises(argparse.ArgumentTypeError):
        main(['--config-file', 'missing.cfg'])


def test_simple_replacement(tmpdir):
    tmpdir.join("VERSION").write("1.2.0")
    tmpdir.chdir()
    main(shlex_split("patch --current-version 1.2.0 --new-version 1.2.1 VERSION"))
    assert "1.2.1" == tmpdir.join("VERSION").read()


def test_simple_replacement_in_utf8_file(tmpdir):
    tmpdir.join("VERSION").write("Kröt1.3.0".encode(), 'wb')
    tmpdir.chdir()
    out = tmpdir.join("VERSION").read('rb')
    main(shlex_split("patch --verbose --current-version 1.3.0 --new-version 1.3.1 VERSION"))
    out = tmpdir.join("VERSION").read('rb')
    assert "'Kr\\xc3\\xb6t1.3.1'" in repr(out)


def test_config_file(tmpdir):
    tmpdir.join("file1").write("0.9.34")
    tmpdir.join("my_bump_config.cfg").write("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
[bumpversion:file:file1]""")

    tmpdir.chdir()
    main(shlex_split("patch --config-file my_bump_config.cfg"))

    assert "0.9.35" == tmpdir.join("file1").read()


def test_default_config_files(tmpdir, configfile):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join(configfile).write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
[bumpversion:file:file2]""")

    tmpdir.chdir()
    main(['patch'])

    assert "0.10.3" == tmpdir.join("file2").read()


def test_glob_keyword(tmpdir, configfile):
    tmpdir.join("file1.txt").write("0.9.34")
    tmpdir.join("file2.txt").write("0.9.34")
    tmpdir.join(configfile).write("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
[bumpversion:glob:*.txt]""")

    tmpdir.chdir()
    main(["patch"])
    assert "0.9.35" == tmpdir.join("file1.txt").read()
    assert "0.9.35" == tmpdir.join("file2.txt").read()

def test_glob_keyword_recursive(tmpdir, configfile):
    tmpdir.mkdir("subdir").mkdir("subdir2")
    file1 = tmpdir.join("subdir").join("file1.txt")
    file1.write("0.9.34")
    file2 = tmpdir.join("subdir").join("subdir2").join("file2.txt")
    file2.write("0.9.34")
    tmpdir.join(configfile).write("""[bumpversion]
current_version: 0.9.34
new_version: 0.9.35
[bumpversion:glob:**/*.txt]""")

    tmpdir.chdir()
    main(["patch"])
    assert "0.9.35" == file1.read()
    assert "0.9.35" == file2.read()


def test_file_keyword_with_suffix_is_accepted(tmpdir, configfile, file_keyword):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join(configfile).write(
        """[bumpversion]
    current_version: 0.10.2
    new_version: 0.10.3
    [bumpversion:%s:file2]
    """ % file_keyword
    )

    tmpdir.chdir()
    main(['patch'])

    assert "0.10.3" == tmpdir.join("file2").read()


def test_multiple_config_files(tmpdir):
    tmpdir.join("file2").write("0.10.2")
    tmpdir.join("setup.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
[bumpversion:file:file2]""")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.4
[bumpversion:file:file2]""")

    tmpdir.chdir()
    main(['patch'])

    assert "0.10.4" == tmpdir.join("file2").read()


def test_single_file_processed_twice(tmpdir):
    """
    Verify that a single file "file2" can be processed twice.

    Use two file_ entries, both with a different suffix after
    the underscore.
    Employ different parse/serialize and search/replace configs
    to verify correct interpretation.
    """
    tmpdir.join("file2").write("dots: 0.10.2\ndashes: 0-10-2")
    tmpdir.join("setup.cfg").write("""[bumpversion]
current_version: 0.10.2
new_version: 0.10.3
[bumpversion:file:file2]""")
    tmpdir.join(".bumpversion.cfg").write(r"""[bumpversion]
current_version: 0.10.2
new_version: 0.10.4
[bumpversion:file (version with dots):file2]
search = dots: {current_version}
replace = dots: {new_version}
[bumpversion:file (version with dashes):file2]
search = dashes: {current_version}
replace = dashes: {new_version}
parse = (?P<major>\d+)-(?P<minor>\d+)-(?P<patch>\d+)
serialize = {major}-{minor}-{patch}
""")

    tmpdir.chdir()
    main(['patch'])

    assert "dots: 0.10.4\ndashes: 0-10-4" == tmpdir.join("file2").read()


def test_config_file_is_updated(tmpdir):
    tmpdir.join("file3").write("0.0.13")
    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 0.0.13
new_version: 0.0.14
[bumpversion:file:file3]""")

    tmpdir.chdir()
    main(['patch', '--verbose'])

    assert """[bumpversion]
current_version = 0.0.14

[bumpversion:file:file3]
""" == tmpdir.join(".bumpversion.cfg").read()


def test_dry_run(tmpdir, vcs):
    tmpdir.chdir()

    config = """[bumpversion]
current_version = 0.12.0
tag = True
commit = True
message = DO NOT BUMP VERSIONS WITH THIS FILE
[bumpversion:file:file4]
"""

    version = "0.12.0"

    tmpdir.join("file4").write(version)
    tmpdir.join(".bumpversion.cfg").write(config)

    check_call([vcs, "init"])
    check_call([vcs, "add", "file4"])
    check_call([vcs, "add", ".bumpversion.cfg"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--dry-run'])

    assert config == tmpdir.join(".bumpversion.cfg").read()
    assert version == tmpdir.join("file4").read()

    vcs_log = check_output([vcs, "log"]).decode('utf-8')

    assert "initial commit" in vcs_log
    assert "DO NOT" not in vcs_log


def test_dry_run_verbose_log(tmpdir, vcs):
    tmpdir.chdir()

    version = "0.12.0"
    patch = "0.12.1"
    v_parts = version.split('.')
    p_parts = patch.split('.')
    file = "file4"
    message = "DO NOT BUMP VERSIONS WITH THIS FILE"
    config = """[bumpversion]
current_version = {version}
tag = True
commit = True
message = {message}

[bumpversion:file:{file}]

""".format(version=version, file=file, message=message)

    bumpcfg = ".bumpversion.cfg"
    tmpdir.join(file).write(version)
    tmpdir.join(bumpcfg).write(config)

    check_call([vcs, "init"])
    check_call([vcs, "add", file])
    check_call([vcs, "add", bumpcfg])
    check_call([vcs, "commit", "-m", "initial commit"])

    with LogCapture(level=logging.INFO) as log_capture:
        main(['patch', '--dry-run', '--verbose'])

    vcs_name = "Mercurial" if vcs == "hg" else "Git"
    log_capture.check_present(
        # generic --verbose entries
        ('bumpversion.cli', 'INFO', 'Reading config file {}:'.format(bumpcfg)),
        ('bumpversion.cli', 'INFO', config),
        ('bumpversion.version_part', 'INFO',
         "Parsing version '{}' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'".format(version)),
        ('bumpversion.version_part', 'INFO',
         'Parsed the following values: major={}, minor={}, patch={}'.format(v_parts[0], v_parts[1], v_parts[2])),
        ('bumpversion.cli', 'INFO', "Attempting to increment part 'patch'"),
        ('bumpversion.cli', 'INFO',
         'Values are now: major={}, minor={}, patch={}'.format(p_parts[0], p_parts[1], p_parts[2])),
        ('bumpversion.cli', 'INFO', "Dry run active, won't touch any files."),  # only in dry-run mode
        ('bumpversion.version_part', 'INFO',
         "Parsing version '{}' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'".format(patch)),
        ('bumpversion.version_part', 'INFO',
         'Parsed the following values: major={}, minor={}, patch={}'.format(p_parts[0], p_parts[1], p_parts[2])),
        ('bumpversion.cli', 'INFO', "New version will be '{}'".format(patch)),
        ('bumpversion.cli', 'INFO', 'Asserting files {} contain the version string...'.format(file)),
        ('bumpversion.utils', 'INFO', "Found '{v}' in {f} at line 0: {v}".format(v=version, f=file)),  # verbose
        ('bumpversion.utils', 'INFO', 'Would change file {}:'.format(file)),  # dry-run change to 'would'
        ('bumpversion.utils', 'INFO',
         '--- a/{f}\n+++ b/{f}\n@@ -1 +1 @@\n-{v}\n+{p}'.format(f=file, v=version, p=patch)),
        ('bumpversion.list', 'INFO', 'current_version={}'.format(version)),
        ('bumpversion.list', 'INFO', 'tag=True'),
        ('bumpversion.list', 'INFO', 'commit=True'),
        ('bumpversion.list', 'INFO', 'message={}'.format(message)),
        ('bumpversion.list', 'INFO', 'new_version={}'.format(patch)),
        ('bumpversion.cli', 'INFO', 'Would write to config file {}:'.format(bumpcfg)),  # dry-run 'would'
        ('bumpversion.cli', 'INFO', config.replace(version, patch)),
        # following entries are only present if both --verbose and --dry-run are specified
        # all entries use 'would do x' variants instead of 'doing x'
        ('bumpversion.cli', 'INFO', 'Would prepare {vcs} commit'.format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would add changes in file '{file}' to {vcs}".format(file=file, vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would add changes in file '{file}' to {vcs}".format(file=bumpcfg, vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would commit to {vcs} with message '{msg}'".format(msg=message, vcs=vcs_name)),
        ('bumpversion.cli', 'INFO',
         "Would tag 'v{p}' with message 'Bump version: {v} → {p}' in {vcs} and not signing"
         .format(v=version, p=patch, vcs=vcs_name)),
        order_matters=True
    )


def test_bump_version(tmpdir):
    tmpdir.join("file5").write("1.0.0")
    tmpdir.chdir()
    main(['patch', '--current-version', '1.0.0', 'file5'])

    assert '1.0.1' == tmpdir.join("file5").read()


def test_bump_version_custom_main(tmpdir):
    tmpdir.join("file6").write("XXX1;0;0")
    tmpdir.chdir()
    main([
         '--current-version', 'XXX1;0;0',
         '--parse', r'XXX(?P<spam>\d+);(?P<blob>\d+);(?P<slurp>\d+)',
         '--serialize', 'XXX{spam};{blob};{slurp}',
         'blob',
         'file6'
         ])

    assert 'XXX1;1;0' == tmpdir.join("file6").read()


def test_bump_version_custom_parse_serialize_configfile(tmpdir):
    tmpdir.join("file12").write("ZZZ8;0;0")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(r"""[bumpversion]
current_version = ZZZ8;0;0
serialize = ZZZ{spam};{blob};{slurp}
parse = ZZZ(?P<spam>\d+);(?P<blob>\d+);(?P<slurp>\d+)
[bumpversion:file:file12]
""")

    main(['blob'])

    assert 'ZZZ8;1;0' == tmpdir.join("file12").read()


def test_bumpversion_custom_parse_semver(tmpdir):
    tmpdir.join("file15").write("XXX1.1.7-master+allan1")
    tmpdir.chdir()
    main([
         '--current-version', '1.1.7-master+allan1',
         '--parse', r'(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)(-(?P<pre_release>[^\+]+))?(\+(?P<meta>.*))?',
         '--serialize', '{major}.{minor}.{patch}-{pre_release}+{meta}',
         'meta',
         'file15'
         ])

    assert 'XXX1.1.7-master+allan2' == tmpdir.join("file15").read()


def test_bump_version_missing_part(tmpdir):
    tmpdir.join("file5").write("1.0.0")
    tmpdir.chdir()
    with pytest.raises(
            exceptions.InvalidVersionPartException,
            match="No part named 'bugfix'"
    ):
        main(['bugfix', '--current-version', '1.0.0', 'file5'])


def test_dirty_work_dir(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("dirty").write("i'm dirty")

    check_call([vcs, "add", "dirty"])
    vcs_name = "Mercurial" if vcs == "hg" else "Git"
    vcs_output = "A dirty" if vcs == "hg" else "A  dirty"

    with pytest.raises(exceptions.WorkingDirectoryIsDirtyException):
        with LogCapture() as log_capture:
            main(['patch', '--current-version', '1', '--new-version', '2', 'file7'])

    log_capture.check_present(
        (
            'bumpversion.cli',
            'WARNING',
            "{} working directory is not clean:\n"
            "{}\n"
            "\n"
            "Use --allow-dirty to override this if you know what you're doing.".format(
                vcs_name,
                vcs_output
            )
        )
    )


def test_force_dirty_work_dir(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("dirty2").write("i'm dirty! 1.1.1")

    check_call([vcs, "add", "dirty2"])

    main([
        'patch',
        '--allow-dirty',
        '--current-version',
        '1.1.1',
        'dirty2'
    ])

    assert "i'm dirty! 1.1.2" == tmpdir.join("dirty2").read()


def test_bump_major(tmpdir):
    tmpdir.join("fileMAJORBUMP").write("4.2.8")
    tmpdir.chdir()
    main(['--current-version', '4.2.8', 'major', 'fileMAJORBUMP'])

    assert '5.0.0' == tmpdir.join("fileMAJORBUMP").read()


def test_commit_and_tag(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("47.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '47.1.1', '--commit', 'VERSION'])

    assert '47.1.2' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-47.1.1' in log
    assert '+47.1.2' in log
    assert 'Bump version: 47.1.1 → 47.1.2' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v47.1.2' not in tag_out

    main(['patch', '--current-version', '47.1.2', '--commit', '--tag', 'VERSION'])

    assert '47.1.3' == tmpdir.join("VERSION").read()

    check_output([vcs, "log", "-p"])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v47.1.3' in tag_out


def test_commit_and_tag_with_configfile(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]\ncommit = True\ntag = True""")

    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("48.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '48.1.1', '--no-tag', 'VERSION'])

    assert '48.1.2' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-48.1.1' in log
    assert '+48.1.2' in log
    assert 'Bump version: 48.1.1 → 48.1.2' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v48.1.2' not in tag_out

    main(['patch', '--current-version', '48.1.2', 'VERSION'])

    assert '48.1.3' == tmpdir.join("VERSION").read()

    check_output([vcs, "log", "-p"])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v48.1.3' in tag_out


@pytest.mark.parametrize("config", [COMMIT, COMMIT_NOT_TAG])
def test_commit_and_not_tag_with_configfile(tmpdir, vcs, config):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(config)

    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("48.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--current-version', '48.1.1', 'VERSION'])

    assert '48.1.2' == tmpdir.join("VERSION").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")

    assert '-48.1.1' in log
    assert '+48.1.2' in log
    assert 'Bump version: 48.1.1 → 48.1.2' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'v48.1.2' not in tag_out


def test_commit_explicitly_false(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 10.0.0
commit = False
tag = False""")

    check_call([vcs, "init"])
    tmpdir.join("tracked_file").write("10.0.0")
    check_call([vcs, "add", "tracked_file"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', 'tracked_file'])

    assert '10.0.1' == tmpdir.join("tracked_file").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "10.0.1" not in log

    diff = check_output([vcs, "diff"]).decode("utf-8")
    assert "10.0.1" in diff


def test_commit_configfile_true_cli_false_override(tmpdir, vcs):
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 27.0.0
commit = True""")

    check_call([vcs, "init"])
    tmpdir.join("dont_commit_file").write("27.0.0")
    check_call([vcs, "add", "dont_commit_file"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main(['patch', '--no-commit', 'dont_commit_file'])

    assert '27.0.1' == tmpdir.join("dont_commit_file").read()

    log = check_output([vcs, "log", "-p"]).decode("utf-8")
    assert "27.0.1" not in log

    diff = check_output([vcs, "diff"]).decode("utf-8")
    assert "27.0.1" in diff


def test_bump_version_environment(tmpdir):
    tmpdir.join("on_jenkins").write("2.3.4")
    tmpdir.chdir()
    os.environ['BUILD_NUMBER'] = "567"
    main([
         '--verbose',
         '--current-version', '2.3.4',
         '--parse', r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*',
         '--serialize', '{major}.{minor}.{patch}.pre{$BUILD_NUMBER}',
         'patch',
         'on_jenkins',
         ])
    del os.environ['BUILD_NUMBER']

    assert '2.3.5.pre567' == tmpdir.join("on_jenkins").read()


def test_current_version_from_tag(tmpdir, git):
    # prepare
    tmpdir.join("update_from_tag").write("26.6.0")
    tmpdir.chdir()
    check_call([git, "init"])
    check_call([git, "add", "update_from_tag"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v26.6.0"])

    # don't give current-version, that should come from tag
    main(['patch', 'update_from_tag'])

    assert '26.6.1' == tmpdir.join("update_from_tag").read()


def test_current_version_from_tag_written_to_config_file(tmpdir, git):
    # prepare
    tmpdir.join("updated_also_in_config_file").write("14.6.0")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]""")

    check_call([git, "init"])
    check_call([git, "add", "updated_also_in_config_file"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v14.6.0"])

    # don't give current-version, that should come from tag
    main([
        'patch',
        'updated_also_in_config_file',
         '--commit',
         '--tag',
         ])

    assert '14.6.1' == tmpdir.join("updated_also_in_config_file").read()
    assert '14.6.1' in tmpdir.join(".bumpversion.cfg").read()


def test_distance_to_latest_tag_as_part_of_new_version(tmpdir, git):
    # prepare
    tmpdir.join("my_source_file").write("19.6.0")
    tmpdir.chdir()

    check_call([git, "init"])
    check_call([git, "add", "my_source_file"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v19.6.0"])
    check_call([git, "commit", "--allow-empty", "-m", "Just a commit 1"])
    check_call([git, "commit", "--allow-empty", "-m", "Just a commit 2"])
    check_call([git, "commit", "--allow-empty", "-m", "Just a commit 3"])

    # don't give current-version, that should come from tag
    main([
         'patch',
         '--parse', r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*',
         '--serialize', '{major}.{minor}.{patch}-pre{distance_to_latest_tag}',
         'my_source_file',
         ])

    assert '19.6.1-pre3' == tmpdir.join("my_source_file").read()


def test_override_vcs_current_version(tmpdir, git):
    # prepare
    tmpdir.join("contains_actual_version").write("6.7.8")
    tmpdir.chdir()
    check_call([git, "init"])
    check_call([git, "add", "contains_actual_version"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v6.7.8"])

    # update file
    tmpdir.join("contains_actual_version").write("7.0.0")
    check_call([git, "add", "contains_actual_version"])

    # but forgot to tag or forgot to push --tags
    check_call([git, "commit", "-m", "major release"])

    # if we don't give current-version here we get
    # "AssertionError: Did not find string 6.7.8 in file contains_actual_version"
    main(['patch', '--current-version', '7.0.0', 'contains_actual_version'])

    assert '7.0.1' == tmpdir.join("contains_actual_version").read()


def test_non_existing_file(tmpdir):
    tmpdir.chdir()
    with pytest.raises(IOError):
        main(shlex_split("patch --current-version 1.2.0 --new-version 1.2.1 does_not_exist.txt"))


def test_non_existing_second_file(tmpdir):
    tmpdir.chdir()
    tmpdir.join("my_source_code.txt").write("1.2.3")
    with pytest.raises(IOError):
        main(shlex_split("patch --current-version 1.2.3 my_source_code.txt does_not_exist2.txt"))

    # first file is unchanged because second didn't exist
    assert '1.2.3' == tmpdir.join("my_source_code.txt").read()


def test_read_version_tags_only(tmpdir, git):
    # prepare
    tmpdir.join("update_from_tag").write("29.6.0")
    tmpdir.chdir()
    check_call([git, "init"])
    check_call([git, "add", "update_from_tag"])
    check_call([git, "commit", "-m", "initial"])
    check_call([git, "tag", "v29.6.0"])
    check_call([git, "commit", "--allow-empty", "-m", "a commit"])
    check_call([git, "tag", "jenkins-deploy-my-project-2"])

    # don't give current-version, that should come from tag
    main(['patch', 'update_from_tag'])

    assert '29.6.1' == tmpdir.join("update_from_tag").read()


def test_tag_name(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("31.1.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main([
        'patch', '--current-version', '31.1.1', '--commit', '--tag',
        'VERSION', '--tag-name', 'ReleasedVersion-{new_version}'
    ])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'ReleasedVersion-31.1.2' in tag_out


def test_message_from_config_file(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("400.0.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version: 400.0.0
new_version: 401.0.0
commit: True
tag: True
message: {current_version} was old, {new_version} is new
tag_name: from-{current_version}-to-{new_version}""")

    main(['major', 'VERSION'])

    log = check_output([vcs, "log", "-p"])

    assert b'400.0.0 was old, 401.0.0 is new' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])

    assert b'from-400.0.0-to-401.0.0' in tag_out


def test_all_parts_in_message_and_serialize_and_tag_name_from_config_file(tmpdir, vcs):
    """
    Ensure that major/minor/patch *and* custom parts can be used everywhere.

    - As [part] in 'serialize'.
    - As new_[part] and previous_[part] in 'message'.
    - As new_[part] and previous_[part] in 'tag_name'.

    In message and tag_name, also ensure that new_version and
    current_version are correct.
    """
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("400.1.2.101")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    tmpdir.join(".bumpversion.cfg").write(r"""[bumpversion]
current_version: 400.1.2.101
new_version: 401.2.3.102
parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).(?P<custom>\d+)
serialize = {major}.{minor}.{patch}.{custom}
commit: True
tag: True
message: {current_version}/{current_major}.{current_minor}.{current_patch} custom {current_custom} becomes {new_version}/{new_major}.{new_minor}.{new_patch} custom {new_custom}
tag_name: from-{current_version}-aka-{current_major}.{current_minor}.{current_patch}-custom-{current_custom}-to-{new_version}-aka-{new_major}.{new_minor}.{new_patch}-custom-{new_custom}

[bumpversion:part:custom]
""")

    main(['major', 'VERSION'])

    log = check_output([vcs, "log", "-p"])
    assert b'400.1.2.101/400.1.2 custom 101 becomes 401.2.3.102/401.2.3 custom 102' in log

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b'from-400.1.2.101-aka-400.1.2-custom-101-to-401.2.3.102-aka-401.2.3-custom-102' in tag_out


def test_all_parts_in_replace_from_config_file(tmpdir, vcs):
    """
    Ensure that major/minor/patch *and* custom parts can be used in 'replace'.
    """
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("my version is 400.1.2.101\n")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    tmpdir.join(".bumpversion.cfg").write(r"""[bumpversion]
current_version: 400.1.2.101
new_version: 401.2.3.102
parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).(?P<custom>\d+)
serialize = {major}.{minor}.{patch}.{custom}
commit: True
tag: False

[bumpversion:part:custom]

[bumpversion:VERSION]
search = my version is {current_version}
replace = my version is {new_major}.{new_minor}.{new_patch}.{new_custom}""")

    main(['major', 'VERSION'])
    log = check_output([vcs, "log", "-p"])
    assert b'+my version is 401.2.3.102' in log


def test_unannotated_tag(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("42.3.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main([
        'patch', '--current-version', '42.3.1', '--commit', '--tag', 'VERSION',
        '--tag-name', 'ReleasedVersion-{new_version}', '--tag-message', ''
    ])

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b'ReleasedVersion-42.3.2' in tag_out

    if vcs == "git":
        describe_out = subprocess.call([vcs, "describe"])
        assert 128 == describe_out

        describe_out = subprocess.check_output([vcs, "describe", "--tags"])
        assert describe_out.startswith(b'ReleasedVersion-42.3.2')


def test_annotated_tag(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("42.4.1")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    main([
        'patch', '--current-version', '42.4.1', '--commit', '--tag',
        'VERSION', '--tag-message', 'test {new_version}-tag']
    )
    assert '42.4.2' == tmpdir.join("VERSION").read()

    tag_out = check_output([vcs, {"git": "tag", "hg": "tags"}[vcs]])
    assert b'v42.4.2' in tag_out

    if vcs == "git":
        describe_out = subprocess.check_output([vcs, "describe"])
        assert describe_out == b'v42.4.2\n'

        describe_out = subprocess.check_output([vcs, "show", "v42.4.2"])
        assert describe_out.startswith(b"tag v42.4.2\n")
        assert b'test 42.4.2-tag' in describe_out
    elif vcs == "hg":
        describe_out = subprocess.check_output([vcs, "log"])
        assert b'test 42.4.2-tag' in describe_out
    else:
        raise ValueError("Unknown VCS")


def test_vcs_describe(tmpdir, git):
    tmpdir.chdir()
    check_call([git, "init"])
    tmpdir.join("VERSION").write("42.5.1")
    check_call([git, "add", "VERSION"])
    check_call([git, "commit", "-m", "initial commit"])

    main([
        'patch', '--current-version', '42.5.1', '--commit', '--tag',
        'VERSION', '--tag-message', 'test {new_version}-tag'
    ])
    assert '42.5.2' == tmpdir.join("VERSION").read()

    describe_out = subprocess.check_output([git, "describe"])
    assert b'v42.5.2\n' == describe_out

    main([
        'patch', '--current-version', '42.5.2', '--commit', '--tag', 'VERSION',
        '--tag-name', 'ReleasedVersion-{new_version}', '--tag-message', ''
    ])
    assert '42.5.3' == tmpdir.join("VERSION").read()

    describe_only_annotated_out = subprocess.check_output([git, "describe"])
    assert describe_only_annotated_out.startswith(b'v42.5.2-1-g')

    describe_all_out = subprocess.check_output([git, "describe", "--tags"])
    assert b'ReleasedVersion-42.5.3\n' == describe_all_out


config_parser_handles_utf8 = True
try:
    import configparser
except ImportError:
    config_parser_handles_utf8 = False


@pytest.mark.xfail(not config_parser_handles_utf8,
                   reason="old ConfigParser uses non-utf-8-strings internally")
def test_utf8_message_from_config_file(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("500.0.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    initial_config = """[bumpversion]
current_version = 500.0.0
commit = True
message = Nová verze: {current_version} ☃, {new_version} ☀

"""

    tmpdir.join(".bumpversion.cfg").write(initial_config.encode('utf-8'), mode='wb')
    main(['major', 'VERSION'])
    check_output([vcs, "log", "-p"])
    expected_new_config = initial_config.replace('500', '501')
    assert expected_new_config.encode('utf-8') == tmpdir.join(".bumpversion.cfg").read(mode='rb')


def test_utf8_message_from_config_file(tmpdir, vcs):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("10.10.0")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    initial_config = """[bumpversion]
current_version = 10.10.0
commit = True
message = [{now}] [{utcnow} {utcnow:%YXX%mYY%d}]

"""
    tmpdir.join(".bumpversion.cfg").write(initial_config)

    main(['major', 'VERSION'])

    log = check_output([vcs, "log", "-p"])

    assert b'[20' in log
    assert b'] [' in log
    assert b'XX' in log
    assert b'YY' in log


def test_commit_and_tag_from_below_vcs_root(tmpdir, vcs, monkeypatch):
    tmpdir.chdir()
    check_call([vcs, "init"])
    tmpdir.join("VERSION").write("30.0.3")
    check_call([vcs, "add", "VERSION"])
    check_call([vcs, "commit", "-m", "initial commit"])

    tmpdir.mkdir("subdir")
    monkeypatch.chdir(tmpdir.join("subdir"))

    main(['major', '--current-version', '30.0.3', '--commit', '../VERSION'])

    assert '31.0.0' == tmpdir.join("VERSION").read()


def test_non_vcs_operations_if_vcs_is_not_installed(tmpdir, vcs, monkeypatch):
    monkeypatch.setenv("PATH", "")

    tmpdir.chdir()
    tmpdir.join("VERSION").write("31.0.3")

    main(['major', '--current-version', '31.0.3', 'VERSION'])

    assert '32.0.0' == tmpdir.join("VERSION").read()


def test_serialize_newline(tmpdir):
    tmpdir.join("file_new_line").write("MAJOR=31\nMINOR=0\nPATCH=3\n")
    tmpdir.chdir()
    main([
        '--current-version', 'MAJOR=31\nMINOR=0\nPATCH=3\n',
        '--parse', 'MAJOR=(?P<major>\\d+)\\nMINOR=(?P<minor>\\d+)\\nPATCH=(?P<patch>\\d+)\\n',
        '--serialize', 'MAJOR={major}\nMINOR={minor}\nPATCH={patch}\n',
        '--verbose',
        'major',
        'file_new_line'
        ])
    assert 'MAJOR=32\nMINOR=0\nPATCH=0\n' == tmpdir.join("file_new_line").read()


def test_multiple_serialize_three_part(tmpdir):
    tmpdir.join("fileA").write("Version: 0.9")
    tmpdir.chdir()
    main([
         '--current-version', 'Version: 0.9',
         '--parse', r'Version:\ (?P<major>\d+)(\.(?P<minor>\d+)(\.(?P<patch>\d+))?)?',
         '--serialize', 'Version: {major}.{minor}.{patch}',
         '--serialize', 'Version: {major}.{minor}',
         '--serialize', 'Version: {major}',
         '--verbose',
         'major',
         'fileA'
         ])

    assert 'Version: 1' == tmpdir.join("fileA").read()


def test_multiple_serialize_two_part(tmpdir):
    tmpdir.join("fileB").write("0.9")
    tmpdir.chdir()
    main([
         '--current-version', '0.9',
         '--parse', r'(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?',
         '--serialize', '{major}.{minor}.{patch}',
         '--serialize', '{major}.{minor}',
         'minor',
         'fileB'
         ])

    assert '0.10' == tmpdir.join("fileB").read()


def test_multiple_serialize_two_part_patch(tmpdir):
    tmpdir.join("fileC").write("0.7")
    tmpdir.chdir()
    main([
         '--current-version', '0.7',
         '--parse', r'(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?',
         '--serialize', '{major}.{minor}.{patch}',
         '--serialize', '{major}.{minor}',
         'patch',
         'fileC'
         ])

    assert '0.7.1' == tmpdir.join("fileC").read()


def test_multiple_serialize_two_part_patch_configfile(tmpdir):
    tmpdir.join("fileD").write("0.6")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(r"""[bumpversion]
current_version = 0.6
serialize =
  {major}.{minor}.{patch}
  {major}.{minor}
parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
[bumpversion:file:fileD]
""")

    main(['patch'])

    assert '0.6.1' == tmpdir.join("fileD").read()


def test_search_uses_shortest_possible_custom_search_pattern(tmpdir):
    config = dedent(r"""
        [bumpversion]
        current_version = 0.0.0
        commit = True
        tag = True
        parse = (?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+).?((?P<prerelease>.*))?
        serialize =
            {major}.{minor}.{patch}.{prerelease}
            {major}.{minor}.{patch}

        [bumpversion:file:package.json]
        search = "version": "{current_version}",
        replace = "version": "{new_version}",
    """)
    tmpdir.join(".bumpversion.cfg").write(config.encode('utf-8'), mode='wb')

    tmpdir.join("package.json").write("""{
        "version": "0.0.0",
        "package": "20.0.0",
    }""")

    tmpdir.chdir()
    main(["patch"])

    assert """{
        "version": "0.0.1",
        "package": "20.0.0",
    }""" == tmpdir.join("package.json").read()


def test_log_no_config_file_info_message(tmpdir):
    tmpdir.chdir()

    tmpdir.join("a_file.txt").write("1.0.0")

    with LogCapture(level=logging.INFO) as log_capture:
        main(['--verbose', '--verbose', '--current-version', '1.0.0', 'patch', 'a_file.txt'])

    log_capture.check_present(
        ('bumpversion.cli', 'INFO', 'Could not read config file at .bumpversion.cfg'),
        ('bumpversion.version_part', 'INFO', "Parsing version '1.0.0' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=1, minor=0, patch=0'),
        ('bumpversion.cli', 'INFO', "Attempting to increment part 'patch'"),
        ('bumpversion.cli', 'INFO', 'Values are now: major=1, minor=0, patch=1'),
        ('bumpversion.version_part', 'INFO', "Parsing version '1.0.1' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=1, minor=0, patch=1'),
        ('bumpversion.cli', 'INFO', "New version will be '1.0.1'"),
        ('bumpversion.cli', 'INFO', 'Asserting files a_file.txt contain the version string...'),
        ('bumpversion.utils', 'INFO', "Found '1.0.0' in a_file.txt at line 0: 1.0.0"),
        ('bumpversion.utils', 'INFO', 'Changing file a_file.txt:'),
        ('bumpversion.utils', 'INFO', '--- a/a_file.txt\n+++ b/a_file.txt\n@@ -1 +1 @@\n-1.0.0\n+1.0.1'),
        ('bumpversion.cli', 'INFO', 'Would write to config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 1.0.1\n\n'),
        order_matters=True
    )


def test_log_parse_doesnt_parse_current_version(tmpdir):
    tmpdir.chdir()

    with LogCapture() as log_capture:
        main(['--verbose', '--parse', 'xxx', '--current-version', '12', '--new-version', '13', 'patch'])

    log_capture.check_present(
        ('bumpversion.cli', 'INFO', "Could not read config file at .bumpversion.cfg"),
        ('bumpversion.version_part', 'INFO', "Parsing version '12' using regexp 'xxx'"),
        ('bumpversion.version_part', 'WARNING', "Evaluating 'parse' option: 'xxx' does not parse current version '12'"),
        ('bumpversion.version_part', 'INFO', "Parsing version '13' using regexp 'xxx'"),
        ('bumpversion.version_part', 'WARNING', "Evaluating 'parse' option: 'xxx' does not parse current version '13'"),
        ('bumpversion.cli', 'INFO', "New version will be '13'"),
        ('bumpversion.cli', 'INFO', "Asserting files  contain the version string..."),
        ('bumpversion.cli', 'INFO', "Would write to config file .bumpversion.cfg:"),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 13\n\n'),
    )


def test_log_invalid_regex_exit(tmpdir):
    tmpdir.chdir()

    with pytest.raises(SystemExit):
        with LogCapture() as log_capture:
            main(['--parse', '*kittens*', '--current-version', '12', '--new-version', '13', 'patch'])

    log_capture.check_present(
        ('bumpversion.version_part', 'ERROR', "--parse '*kittens*' is not a valid regex"),
    )


def test_complex_info_logging(tmpdir):
    tmpdir.join("fileE").write("0.4")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version = 0.4
        serialize =
          {major}.{minor}.{patch}
          {major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        [bumpversion:file:fileE]
        """).strip())

    with LogCapture() as log_capture:
        main(['patch', '--verbose'])

    log_capture.check(
        ('bumpversion.cli', 'INFO', 'Reading config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 0.4\nserialize =\n  {major}.{minor}.{patch}\n  {major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n[bumpversion:file:fileE]'),
        ('bumpversion.version_part', 'INFO', "Parsing version '0.4' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=0, minor=4, patch=0'),
        ('bumpversion.cli', 'INFO', "Attempting to increment part 'patch'"),
        ('bumpversion.cli', 'INFO', 'Values are now: major=0, minor=4, patch=1'),
        ('bumpversion.version_part', 'INFO', "Parsing version '0.4.1' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=0, minor=4, patch=1'),
        ('bumpversion.cli', 'INFO', "New version will be '0.4.1'"),
        ('bumpversion.cli', 'INFO', 'Asserting files fileE contain the version string...'),
        ('bumpversion.utils', 'INFO', "Found '0.4' in fileE at line 0: 0.4"),
        ('bumpversion.utils', 'INFO', 'Changing file fileE:'),
        ('bumpversion.utils', 'INFO', '--- a/fileE\n+++ b/fileE\n@@ -1 +1 @@\n-0.4\n+0.4.1'),
        ('bumpversion.list', 'INFO', 'current_version=0.4'),
        ('bumpversion.list', 'INFO', 'serialize=\n{major}.{minor}.{patch}\n{major}.{minor}'),
        ('bumpversion.list', 'INFO', 'parse=(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'),
        ('bumpversion.list', 'INFO', 'new_version=0.4.1'),
        ('bumpversion.cli', 'INFO', 'Writing to config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 0.4.1\nserialize = \n\t{major}.{minor}.{patch}\n\t{major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n\n[bumpversion:file:fileE]\n\n')
    )


def test_subjunctive_dry_run_logging(tmpdir, vcs):
    tmpdir.join("dont_touch_me.txt").write("0.8")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version = 0.8
        commit = True
        tag = True
        serialize =
        	{major}.{minor}.{patch}
        	{major}.{minor}
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<patch>\d+))?
        [bumpversion:file:dont_touch_me.txt]
    """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "dont_touch_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    vcs_name = 'Mercurial' if vcs == 'hg' else 'Git'

    with LogCapture() as log_capture:
        main(['patch', '--verbose', '--dry-run'])

    log_capture.check(
        ('bumpversion.cli', 'INFO', 'Reading config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 0.8\ncommit = True\ntag = True\nserialize =\n\t{major}.{minor}.{patch}\n\t{major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n[bumpversion:file:dont_touch_me.txt]'),
        ('bumpversion.version_part', 'INFO', "Parsing version '0.8' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=0, minor=8, patch=0'),
        ('bumpversion.cli', 'INFO', "Attempting to increment part 'patch'"),
        ('bumpversion.cli', 'INFO', 'Values are now: major=0, minor=8, patch=1'),
        ('bumpversion.cli', 'INFO', "Dry run active, won't touch any files."),
        ('bumpversion.version_part', 'INFO', "Parsing version '0.8.1' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=0, minor=8, patch=1'),
        ('bumpversion.cli', 'INFO', "New version will be '0.8.1'"),
        ('bumpversion.cli', 'INFO', 'Asserting files dont_touch_me.txt contain the version string...'),
        ('bumpversion.utils', 'INFO', "Found '0.8' in dont_touch_me.txt at line 0: 0.8"),
        ('bumpversion.utils', 'INFO', 'Would change file dont_touch_me.txt:'),
        ('bumpversion.utils', 'INFO', '--- a/dont_touch_me.txt\n+++ b/dont_touch_me.txt\n@@ -1 +1 @@\n-0.8\n+0.8.1'),
        ('bumpversion.list', 'INFO', 'current_version=0.8'),
        ('bumpversion.list', 'INFO', 'commit=True'),
        ('bumpversion.list', 'INFO', 'tag=True'),
        ('bumpversion.list', 'INFO', 'serialize=\n{major}.{minor}.{patch}\n{major}.{minor}'),
        ('bumpversion.list', 'INFO', 'parse=(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?'),
        ('bumpversion.list', 'INFO', 'new_version=0.8.1'),
        ('bumpversion.cli', 'INFO', 'Would write to config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 0.8.1\ncommit = True\ntag = True\nserialize = \n\t{major}.{minor}.{patch}\n\t{major}.{minor}\nparse = (?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<patch>\\d+))?\n\n[bumpversion:file:dont_touch_me.txt]\n\n'),
        ('bumpversion.cli', 'INFO', 'Would prepare {vcs} commit'.format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would add changes in file 'dont_touch_me.txt' to {vcs}".format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would add changes in file '.bumpversion.cfg' to {vcs}".format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would commit to {vcs} with message 'Bump version: 0.8 \u2192 0.8.1'".format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would tag 'v0.8.1' with message 'Bump version: 0.8 \u2192 0.8.1' in {vcs} and not signing".format(vcs=vcs_name))
    )


def test_log_commit_message_if_no_commit_tag_but_usable_vcs(tmpdir, vcs):
    tmpdir.join("please_touch_me.txt").write("0.3.3")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 0.3.3
        commit = False
        tag = False
        [bumpversion:file:please_touch_me.txt]
        """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_touch_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    vcs_name = 'Mercurial' if vcs == 'hg' else 'Git'

    with LogCapture() as log_capture:
        main(['patch', '--verbose'])

    log_capture.check(
        ('bumpversion.cli', 'INFO', 'Reading config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 0.3.3\ncommit = False\ntag = False\n[bumpversion:file:please_touch_me.txt]'),
        ('bumpversion.version_part', 'INFO', "Parsing version '0.3.3' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=0, minor=3, patch=3'),
        ('bumpversion.cli', 'INFO', "Attempting to increment part 'patch'"),
        ('bumpversion.cli', 'INFO', 'Values are now: major=0, minor=3, patch=4'),
        ('bumpversion.version_part', 'INFO', "Parsing version '0.3.4' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=0, minor=3, patch=4'),
        ('bumpversion.cli', 'INFO', "New version will be '0.3.4'"),
        ('bumpversion.cli', 'INFO', 'Asserting files please_touch_me.txt contain the version string...'),
        ('bumpversion.utils', 'INFO', "Found '0.3.3' in please_touch_me.txt at line 0: 0.3.3"),
        ('bumpversion.utils', 'INFO', 'Changing file please_touch_me.txt:'),
        ('bumpversion.utils', 'INFO', '--- a/please_touch_me.txt\n+++ b/please_touch_me.txt\n@@ -1 +1 @@\n-0.3.3\n+0.3.4'),
        ('bumpversion.list', 'INFO', 'current_version=0.3.3'),
        ('bumpversion.list', 'INFO', 'commit=False'),
        ('bumpversion.list', 'INFO', 'tag=False'),
        ('bumpversion.list', 'INFO', 'new_version=0.3.4'),
        ('bumpversion.cli', 'INFO', 'Writing to config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 0.3.4\ncommit = False\ntag = False\n\n[bumpversion:file:please_touch_me.txt]\n\n'),
        ('bumpversion.cli', 'INFO', 'Would prepare {vcs} commit'.format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would add changes in file 'please_touch_me.txt' to {vcs}".format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would add changes in file '.bumpversion.cfg' to {vcs}".format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would commit to {vcs} with message 'Bump version: 0.3.3 \u2192 0.3.4'".format(vcs=vcs_name)),
        ('bumpversion.cli', 'INFO', "Would tag 'v0.3.4' with message 'Bump version: 0.3.3 \u2192 0.3.4' in {vcs} and not signing".format(vcs=vcs_name)),
    )


def test_listing(tmpdir, vcs):
    tmpdir.join("please_list_me.txt").write("0.5.5")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 0.5.5
        commit = False
        tag = False
        [bumpversion:file:please_list_me.txt]
        """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_list_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    with LogCapture() as log_capture:
        main(['--list', 'patch'])

    log_capture.check(
        ('bumpversion.list', 'INFO', 'current_version=0.5.5'),
        ('bumpversion.list', 'INFO', 'commit=False'),
        ('bumpversion.list', 'INFO', 'tag=False'),
        ('bumpversion.list', 'INFO', 'new_version=0.5.6'),
    )


def test_no_list_no_stdout(tmpdir, vcs):
    tmpdir.join("please_dont_list_me.txt").write("0.5.5")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        files = please_dont_list_me.txt
        current_version = 0.5.5
        commit = False
        tag = False
        """).strip())

    check_call([vcs, "init"])
    check_call([vcs, "add", "please_dont_list_me.txt"])
    check_call([vcs, "commit", "-m", "initial commit"])

    out = run(
        ['bumpversion', 'patch'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.decode('utf-8')

    assert out == ""


def test_bump_non_numeric_parts(tmpdir):
    tmpdir.join("with_pre_releases.txt").write("1.5.dev")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version = 1.5.dev
        parse = (?P<major>\d+)\.(?P<minor>\d+)(\.(?P<release>[a-z]+))?
        serialize =
          {major}.{minor}.{release}
          {major}.{minor}

        [bumpversion:part:release]
        optional_value = gamma
        values =
          dev
          gamma
        [bumpversion:file:with_pre_releases.txt]
        """).strip())

    main(['release', '--verbose'])

    assert '1.5' == tmpdir.join("with_pre_releases.txt").read()

    main(['minor', '--verbose'])

    assert '1.6.dev' == tmpdir.join("with_pre_releases.txt").read()


def test_optional_value_from_documentation(tmpdir):
    tmpdir.join("optional_value_from_doc.txt").write("1.alpha")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
      [bumpversion]
      current_version = 1.alpha
      parse = (?P<num>\d+)(\.(?P<release>.*))?(\.)?
      serialize =
        {num}.{release}
        {num}

      [bumpversion:part:release]
      optional_value = gamma
      values =
        alpha
        beta
        gamma

      [bumpversion:file:optional_value_from_doc.txt]
      """).strip())

    main(['release', '--verbose'])

    assert '1.beta' == tmpdir.join("optional_value_from_doc.txt").read()

    main(['release', '--verbose'])

    assert '1' == tmpdir.join("optional_value_from_doc.txt").read()


def test_python_pre_release_release_post_release(tmpdir):
    tmpdir.join("python386.txt").write("1.0a")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version = 1.0a

        # adapted from http://legacy.python.org/dev/peps/pep-0386/#the-new-versioning-algorithm
        parse = ^
            (?P<major>\d+)\.(?P<minor>\d+)   # minimum 'N.N'
            (?:
                (?P<prerel>[abc]|rc|dev)     # 'a' = alpha, 'b' = beta
                                             # 'c' or 'rc' = release candidate
                (?:
                    (?P<prerelversion>\d+(?:\.\d+)*)
                )?
            )?
            (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?

        serialize =
          {major}.{minor}{prerel}{prerelversion}
          {major}.{minor}{prerel}
          {major}.{minor}

        [bumpversion:part:prerel]
        optional_value = d
        values =
          dev
          a
          b
          c
          rc
          d
        [bumpversion:file:python386.txt]
        """))

    def file_content():
        return tmpdir.join("python386.txt").read()

    main(['prerel'])
    assert '1.0b' == file_content()

    main(['prerelversion'])
    assert '1.0b1' == file_content()

    main(['prerelversion'])
    assert '1.0b2' == file_content()

    main(['prerel'])  # now it's 1.0c
    main(['prerel'])
    assert '1.0rc' == file_content()

    main(['prerel'])
    assert '1.0' == file_content()

    main(['minor'])
    assert '1.1dev' == file_content()

    main(['prerel', '--verbose'])
    assert '1.1a' == file_content()


def test_part_first_value(tmpdir):
    tmpdir.join("the_version.txt").write("0.9.4")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 0.9.4

        [bumpversion:part:minor]
        first_value = 1

        [bumpversion:file:the_version.txt]
        """))

    main(['major', '--verbose'])

    assert '1.1.0' == tmpdir.join("the_version.txt").read()


def test_multi_file_configuration(tmpdir):
    tmpdir.join("FULL_VERSION.txt").write("1.0.3")
    tmpdir.join("MAJOR_VERSION.txt").write("1")

    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version = 1.0.3

        [bumpversion:file:FULL_VERSION.txt]

        [bumpversion:file:MAJOR_VERSION.txt]
        serialize = {major}
        parse = \d+

        """))

    main(['major', '--verbose'])
    assert '2.0.0' in tmpdir.join("FULL_VERSION.txt").read()
    assert '2' in tmpdir.join("MAJOR_VERSION.txt").read()

    main(['patch'])
    assert '2.0.1' in tmpdir.join("FULL_VERSION.txt").read()
    assert '2' in tmpdir.join("MAJOR_VERSION.txt").read()


def test_multi_file_configuration2(tmpdir):
    tmpdir.join("setup.cfg").write("1.6.6")
    tmpdir.join("README.txt").write("MyAwesomeSoftware(TM) v1.6")
    tmpdir.join("BUILD_NUMBER").write("1.6.6+joe+38943")

    tmpdir.chdir()

    tmpdir.join(r".bumpversion.cfg").write(dedent(r"""
      [bumpversion]
      current_version = 1.6.6

      [something:else]

      [foo]

      [bumpversion:file:setup.cfg]

      [bumpversion:file:README.txt]
      parse = '(?P<major>\d+)\.(?P<minor>\d+)'
      serialize =
        {major}.{minor}

      [bumpversion:file:BUILD_NUMBER]
      serialize =
        {major}.{minor}.{patch}+{$USER}+{$BUILD_NUMBER}

      """))

    os.environ['BUILD_NUMBER'] = "38944"
    os.environ['USER'] = "bob"
    main(['minor', '--verbose'])
    del os.environ['BUILD_NUMBER']
    del os.environ['USER']

    assert '1.7.0' in tmpdir.join("setup.cfg").read()
    assert 'MyAwesomeSoftware(TM) v1.7' in tmpdir.join("README.txt").read()
    assert '1.7.0+bob+38944' in tmpdir.join("BUILD_NUMBER").read()

    os.environ['BUILD_NUMBER'] = "38945"
    os.environ['USER'] = "bob"
    main(['patch', '--verbose'])
    del os.environ['BUILD_NUMBER']
    del os.environ['USER']

    assert '1.7.1' in tmpdir.join("setup.cfg").read()
    assert 'MyAwesomeSoftware(TM) v1.7' in tmpdir.join("README.txt").read()
    assert '1.7.1+bob+38945' in tmpdir.join("BUILD_NUMBER").read()


def test_search_replace_to_avoid_updating_unconcerned_lines(tmpdir):
    tmpdir.chdir()

    tmpdir.join("requirements.txt").write("Django>=1.5.6,<1.6\nMyProject==1.5.6")
    tmpdir.join("CHANGELOG.md").write(dedent("""
    # https://keepachangelog.com/en/1.0.0/

    ## [Unreleased]
    ### Added
    - Foobar

    ## [0.0.1] - 2014-05-31
    ### Added
    - This CHANGELOG file to hopefully serve as an evolving example of a
      standardized open source project CHANGELOG.
    """))

    tmpdir.join(".bumpversion.cfg").write(dedent("""
      [bumpversion]
      current_version = 1.5.6

      [bumpversion:file:requirements.txt]
      search = MyProject=={current_version}
      replace = MyProject=={new_version}

      [bumpversion:file:CHANGELOG.md]
      search = {#}{#} [Unreleased]
      replace = {#}{#} [Unreleased]

        {#}{#} [{new_version}] - {utcnow:%Y-%m-%d}
      """).strip())

    with LogCapture() as log_capture:
        main(['minor', '--verbose'])

    utc_today = datetime.utcnow().strftime("%Y-%m-%d")

    log_capture.check(
        ('bumpversion.cli', 'INFO', 'Reading config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 1.5.6\n\n[bumpversion:file:requirements.txt]\nsearch = MyProject=={current_version}\nreplace = MyProject=={new_version}\n\n[bumpversion:file:CHANGELOG.md]\nsearch = {#}{#} [Unreleased]\nreplace = {#}{#} [Unreleased]\n\n  {#}{#} [{new_version}] - {utcnow:%Y-%m-%d}'),
        ('bumpversion.version_part', 'INFO', "Parsing version '1.5.6' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=1, minor=5, patch=6'),
        ('bumpversion.cli', 'INFO', "Attempting to increment part 'minor'"),
        ('bumpversion.cli', 'INFO', 'Values are now: major=1, minor=6, patch=0'),
        ('bumpversion.version_part', 'INFO', "Parsing version '1.6.0' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'"),
        ('bumpversion.version_part', 'INFO', 'Parsed the following values: major=1, minor=6, patch=0'),
        ('bumpversion.cli', 'INFO', "New version will be '1.6.0'"),
        ('bumpversion.cli', 'INFO', 'Asserting files requirements.txt, CHANGELOG.md contain the version string...'),
        ('bumpversion.utils', 'INFO', "Found 'MyProject==1.5.6' in requirements.txt at line 1: MyProject==1.5.6"),
        ('bumpversion.utils', 'INFO', "Found '## [Unreleased]' in CHANGELOG.md at line 3: ## [Unreleased]"),
        ('bumpversion.utils', 'INFO', 'Changing file requirements.txt:'),
        ('bumpversion.utils', 'INFO', '--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1,2 +1,2 @@\n Django>=1.5.6,<1.6\n-MyProject==1.5.6\n+MyProject==1.6.0'),
        ('bumpversion.utils', 'INFO', 'Changing file CHANGELOG.md:'),
        ('bumpversion.utils', 'INFO', '--- a/CHANGELOG.md\n+++ b/CHANGELOG.md\n@@ -2,6 +2,8 @@\n # https://keepachangelog.com/en/1.0.0/\n \n ## [Unreleased]\n+\n+## [1.6.0] - %s\n ### Added\n - Foobar\n ' % utc_today),
        ('bumpversion.list', 'INFO', 'current_version=1.5.6'),
        ('bumpversion.list', 'INFO', 'new_version=1.6.0'),
        ('bumpversion.cli', 'INFO', 'Writing to config file .bumpversion.cfg:'),
        ('bumpversion.cli', 'INFO', '[bumpversion]\ncurrent_version = 1.6.0\n\n[bumpversion:file:requirements.txt]\nsearch = MyProject=={current_version}\nreplace = MyProject=={new_version}\n\n[bumpversion:file:CHANGELOG.md]\nsearch = {#}{#} [Unreleased]\nreplace = {#}{#} [Unreleased]\n\t\n\t{#}{#} [{new_version}] - {utcnow:%Y-%m-%d}\n\n')
     )

    assert 'MyProject==1.6.0' in tmpdir.join("requirements.txt").read()
    assert 'Django>=1.5.6' in tmpdir.join("requirements.txt").read()


def test_search_replace_expanding_changelog(tmpdir):
    tmpdir.chdir()

    tmpdir.join("CHANGELOG.md").write(dedent("""
    My awesome software project Changelog
    =====================================

    Unreleased
    ----------

    * Some nice feature
    * Some other nice feature

    Version v8.1.1 (2014-05-28)
    ---------------------------

    * Another old nice feature

    """))

    config_content = dedent("""
      [bumpversion]
      current_version = 8.1.1

      [bumpversion:file:CHANGELOG.md]
      search =
        Unreleased
        ----------
      replace =
        Unreleased
        ----------
        Version v{new_version} ({now:%Y-%m-%d})
        ---------------------------
    """)

    tmpdir.join(".bumpversion.cfg").write(config_content)

    with mock.patch("bumpversion.cli.logger"):
        main(['minor', '--verbose'])

    predate = dedent('''
      Unreleased
      ----------
      Version v8.2.0 (20
      ''').strip()

    postdate = dedent('''
      )
      ---------------------------

      * Some nice feature
      * Some other nice feature
      ''').strip()

    assert predate in tmpdir.join("CHANGELOG.md").read()
    assert postdate in tmpdir.join("CHANGELOG.md").read()


def test_non_matching_search_does_not_modify_file(tmpdir):
    tmpdir.chdir()

    changelog_content = dedent("""
    # Unreleased
    
    * bullet point A
    
    # Release v'older' (2019-09-17)
    
    * bullet point B
    """)

    config_content = dedent("""
      [bumpversion]
      current_version = 1.0.3

      [bumpversion:file:CHANGELOG.md]
      search = Not-yet-released
      replace = Release v{new_version} ({now:%Y-%m-%d})
    """)

    tmpdir.join("CHANGELOG.md").write(changelog_content)
    tmpdir.join(".bumpversion.cfg").write(config_content)

    with pytest.raises(
            exceptions.VersionNotFoundException,
            match="Did not find 'Not-yet-released' in file: 'CHANGELOG.md'"
    ):
        main(['patch', '--verbose'])

    assert changelog_content == tmpdir.join("CHANGELOG.md").read()
    assert config_content in tmpdir.join(".bumpversion.cfg").read()


def test_search_replace_cli(tmpdir):
    tmpdir.join("file89").write("My birthday: 3.5.98\nCurrent version: 3.5.98")
    tmpdir.chdir()
    main([
         '--current-version', '3.5.98',
         '--search', 'Current version: {current_version}',
         '--replace', 'Current version: {new_version}',
         'minor',
         'file89',
         ])

    assert 'My birthday: 3.5.98\nCurrent version: 3.6.0' == tmpdir.join("file89").read()


def test_deprecation_warning_files_in_global_configuration(tmpdir):
    tmpdir.chdir()

    tmpdir.join("fileX").write("3.2.1")
    tmpdir.join("fileY").write("3.2.1")
    tmpdir.join("fileZ").write("3.2.1")

    tmpdir.join(".bumpversion.cfg").write("""[bumpversion]
current_version = 3.2.1
files = fileX fileY fileZ
""")

    warning_registry = getattr(bumpversion, '__warningregistry__', None)
    if warning_registry:
        warning_registry.clear()
    warnings.resetwarnings()
    warnings.simplefilter('always')
    with warnings.catch_warnings(record=True) as received_warnings:
        main(['patch'])

    w = received_warnings.pop()
    assert issubclass(w.category, PendingDeprecationWarning)
    assert "'files =' configuration will be deprecated, please use" in str(w.message)


def test_deprecation_warning_multiple_files_cli(tmpdir):
    tmpdir.chdir()

    tmpdir.join("fileA").write("1.2.3")
    tmpdir.join("fileB").write("1.2.3")
    tmpdir.join("fileC").write("1.2.3")

    warning_registry = getattr(bumpversion, '__warningregistry__', None)
    if warning_registry:
        warning_registry.clear()
    warnings.resetwarnings()
    warnings.simplefilter('always')
    with warnings.catch_warnings(record=True) as received_warnings:
        main(['--current-version', '1.2.3', 'patch', 'fileA', 'fileB', 'fileC'])

    w = received_warnings.pop()
    assert issubclass(w.category, PendingDeprecationWarning)
    assert 'Giving multiple files on the command line will be deprecated' in str(w.message)


def test_file_specific_config_inherits_parse_serialize(tmpdir):
    tmpdir.chdir()

    tmpdir.join("todays_ice_cream").write("14-chocolate")
    tmpdir.join("todays_cake").write("14-chocolate")

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
      [bumpversion]
      current_version = 14-chocolate
      parse = (?P<major>\d+)(\-(?P<flavor>[a-z]+))?
      serialize =
          {major}-{flavor}
          {major}

      [bumpversion:file:todays_ice_cream]
      serialize =
          {major}-{flavor}

      [bumpversion:file:todays_cake]

      [bumpversion:part:flavor]
      values =
          vanilla
          chocolate
          strawberry
      """))

    main(['flavor'])

    assert '14-strawberry' == tmpdir.join("todays_cake").read()
    assert '14-strawberry' == tmpdir.join("todays_ice_cream").read()

    main(['major'])

    assert '15-vanilla' == tmpdir.join("todays_ice_cream").read()
    assert '15' == tmpdir.join("todays_cake").read()


def test_multi_line_search_is_found(tmpdir):
    tmpdir.chdir()

    tmpdir.join("the_alphabet.txt").write(dedent("""
      A
      B
      C
    """))

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 9.8.7

    [bumpversion:file:the_alphabet.txt]
    search =
      A
      B
      C
    replace =
      A
      B
      C
      {new_version}
      """).strip())

    main(['major'])

    assert dedent("""
      A
      B
      C
      10.0.0
    """) == tmpdir.join("the_alphabet.txt").read()


@xfail_if_old_configparser
def test_configparser_empty_lines_in_values(tmpdir):
    tmpdir.chdir()

    tmpdir.join("CHANGES.rst").write(dedent("""
    My changelog
    ============

    current
    -------

    """))

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 0.4.1

    [bumpversion:file:CHANGES.rst]
    search =
      current
      -------
    replace = current
      -------


      {new_version}
      -------
      """).strip())

    main(['patch'])
    assert dedent("""
      My changelog
      ============
      current
      -------


      0.4.2
      -------

    """) == tmpdir.join("CHANGES.rst").read()


def test_regression_tag_name_with_hyphens(tmpdir, git):
    tmpdir.chdir()
    tmpdir.join("some_source.txt").write("2014.10.22")
    check_call([git, "init"])
    check_call([git, "add", "some_source.txt"])
    check_call([git, "commit", "-m", "initial commit"])
    check_call([git, "tag", "very-unrelated-but-containing-lots-of-hyphens"])

    tmpdir.join(".bumpversion.cfg").write(dedent("""
    [bumpversion]
    current_version = 2014.10.22
    """))

    main(['patch', 'some_source.txt'])


def test_unclean_repo_exception(tmpdir, git, caplog):
    tmpdir.chdir()

    config = """[bumpversion]
current_version = 0.0.0
tag = True
commit = True
message = XXX
"""

    tmpdir.join("file1").write("foo")

    # If I have a repo with an initial commit
    check_call([git, "init"])
    check_call([git, "add", "file1"])
    check_call([git, "commit", "-m", "initial commit"])

    # If I add the bumpversion config, uncommitted
    tmpdir.join(".bumpversion.cfg").write(config)

    # I expect bumpversion patch to fail
    with pytest.raises(subprocess.CalledProcessError):
        main(['patch'])

    # And return the output of the failing command
    assert "Failed to run" in caplog.text


def test_regression_characters_after_last_label_serialize_string(tmpdir):
    tmpdir.chdir()
    tmpdir.join("bower.json").write('''
    {
      "version": "1.0.0",
      "dependency1": "1.0.0",
    }
    ''')

    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
    [bumpversion]
    current_version = 1.0.0

    [bumpversion:file:bower.json]
    parse = "version": "(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    serialize = "version": "{major}.{minor}.{patch}"
    """))

    main(['patch', 'bower.json'])


def test_regression_dont_touch_capitalization_of_keys_in_config(tmpdir):
    tmpdir.chdir()
    tmpdir.join("setup.cfg").write(dedent("""
    [bumpversion]
    current_version = 0.1.0

    [other]
    DJANGO_SETTINGS = Value
    """))

    main(['patch'])

    assert dedent("""
    [bumpversion]
    current_version = 0.1.1

    [other]
    DJANGO_SETTINGS = Value
    """).strip() == tmpdir.join("setup.cfg").read().strip()


def test_regression_new_version_cli_in_files(tmpdir):
    """
    Reported here: https://github.com/peritus/bumpversion/issues/60
    """
    tmpdir.chdir()
    tmpdir.join("myp___init__.py").write("__version__ = '0.7.2'")
    tmpdir.chdir()

    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 0.7.2
        message = v{new_version}
        tag_name = {new_version}
        tag = true
        commit = true
        [bumpversion:file:myp___init__.py]
        """).strip())

    main("patch --allow-dirty --verbose --new-version 0.9.3".split(" "))

    assert "__version__ = '0.9.3'" == tmpdir.join("myp___init__.py").read()
    assert "current_version = 0.9.3" in tmpdir.join(".bumpversion.cfg").read()


def test_correct_interpolation_for_setup_cfg_files(tmpdir, configfile):
    """
    Reported here: https://github.com/c4urself/bump2version/issues/21
    """
    tmpdir.chdir()
    tmpdir.join("file.py").write("XX-XX-XXXX v. X.X.X")
    tmpdir.chdir()

    if configfile == "setup.cfg":
        tmpdir.join(configfile).write(dedent("""
            [bumpversion]
            current_version = 0.7.2
            search = XX-XX-XXXX v. X.X.X
            replace = {now:%%m-%%d-%%Y} v. {new_version}
            [bumpversion:file:file.py]
            """).strip())
    else:
        tmpdir.join(configfile).write(dedent("""
            [bumpversion]
            current_version = 0.7.2
            search = XX-XX-XXXX v. X.X.X
            replace = {now:%m-%d-%Y} v. {new_version}
            [bumpversion:file:file.py]
            """).strip())

    main(["major"])

    assert datetime.now().strftime('%m-%d-%Y') + ' v. 1.0.0' == tmpdir.join("file.py").read()
    assert "current_version = 1.0.0" in tmpdir.join(configfile).read()


@pytest.mark.parametrize("newline", [b'\n', b'\r\n'])
def test_retain_newline(tmpdir, configfile, newline):
    tmpdir.join("file.py").write_binary(dedent("""
        0.7.2
        Some Content
        """).strip().encode(encoding='UTF-8').replace(b'\n', newline))
    tmpdir.chdir()

    tmpdir.join(configfile).write_binary(dedent("""
        [bumpversion]
        current_version = 0.7.2
        search = {current_version}
        replace = {new_version}
        [bumpversion:file:file.py]
        """).strip().encode(encoding='UTF-8').replace(b'\n', newline))

    main(["major"])

    assert newline in tmpdir.join("file.py").read_binary()
    new_config = tmpdir.join(configfile).read_binary()
    assert newline in new_config

    # Ensure there is only a single newline (not two) at the end of the file
    # and that it is of the right type
    assert new_config.endswith(b"[bumpversion:file:file.py]" + newline)


def test_no_configured_files(tmpdir, vcs):
    tmpdir.join("please_ignore_me.txt").write("0.5.5")
    tmpdir.chdir()
    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 1.1.1
        [bumpversion:file:please_ignore_me.txt]
        """).strip())
    main(['--no-configured-files', 'patch'])
    assert "0.5.5" == tmpdir.join("please_ignore_me.txt").read()


def test_no_configured_files_still_file_args_work(tmpdir, vcs):
    tmpdir.join("please_ignore_me.txt").write("0.5.5")
    tmpdir.join("please_update_me.txt").write("1.1.1")
    tmpdir.chdir()
    tmpdir.join(".bumpversion.cfg").write(dedent("""
        [bumpversion]
        current_version = 1.1.1
        [bumpversion:file:please_ignore_me.txt]
        """).strip())
    main(['--no-configured-files', 'patch', "please_update_me.txt"])
    assert "0.5.5" == tmpdir.join("please_ignore_me.txt").read()
    assert "1.1.2" == tmpdir.join("please_update_me.txt").read()


class TestSplitArgsInOptionalAndPositional:

    def test_all_optional(self):
        params = ['--allow-dirty', '--verbose', '-n', '--tag-name', '"Tag"']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == []
        assert optional == params

    def test_all_positional(self):
        params = ['minor', 'setup.py']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == params
        assert optional == []

    def test_no_args(self):
        assert split_args_in_optional_and_positional([]) == \
            ([], [])

    def test_short_optionals(self):
        params = ['-m', '"Commit"', '-n']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == []
        assert optional == params

    def test_1optional_2positional(self):
        params = ['-n', 'major', 'setup.py']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == ['major', 'setup.py']
        assert optional == ['-n']

    def test_2optional_1positional(self):
        params = ['-n', '-m', '"Commit"', 'major']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == ['major']
        assert optional == ['-n', '-m', '"Commit"']

    def test_2optional_mixed_2positional(self):
        params = ['--allow-dirty', '-m', '"Commit"', 'minor', 'setup.py']
        positional, optional = \
            split_args_in_optional_and_positional(params)

        assert positional == ['minor', 'setup.py']
        assert optional == ['--allow-dirty', '-m', '"Commit"']


def test_build_number_configuration(tmpdir):
    tmpdir.join("VERSION.txt").write("2.1.6-5123")
    tmpdir.chdir()
    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version: 2.1.6-5123
        parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<build>\d+)
        serialize = {major}.{minor}.{patch}-{build}

        [bumpversion:file:VERSION.txt]

        [bumpversion:part:build]
        independent = True
        """))

    main(['build'])
    assert '2.1.6-5124' == tmpdir.join("VERSION.txt").read()

    main(['major'])
    assert '3.0.0-5124' == tmpdir.join("VERSION.txt").read()

    main(['build'])
    assert '3.0.0-5125' == tmpdir.join("VERSION.txt").read()


def test_independent_falsy_value_in_config_does_not_bump_independently(tmpdir):
    tmpdir.join("VERSION").write("2.1.0-5123")
    tmpdir.chdir()
    tmpdir.join(".bumpversion.cfg").write(dedent(r"""
        [bumpversion]
        current_version: 2.1.0-5123
        parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\-(?P<build>\d+)
        serialize = {major}.{minor}.{patch}-{build}

        [bumpversion:file:VERSION]

        [bumpversion:part:build]
        independent = 0
        """))

    main(['build'])
    assert '2.1.0-5124' == tmpdir.join("VERSION").read()

    main(['major'])
    assert '3.0.0-0' == tmpdir.join("VERSION").read()
