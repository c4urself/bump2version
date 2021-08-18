**unreleased**
**v1.0.2-dev**
- Housekeeping: migrated from travis+appveyor to GitHub Actions for CI, thanks @clbarnes

**v1.0.1**
- Added: enable special characters in search/replace, thanks @mckelvin
- Added: allow globbing a pattern to match multiple files, thanks @balrok
- Added: way to only bump a specified file via --no-configured-files, thanks @balrok
- Fixed: dry-run now correctly outputs, thanks @fmigneault
- Housekeeping: documentation for lightweight tags improved, thanks @GreatBahram
- Housekeeping: added related tools document, thanks @florisla
- Fixed: no more falling back to default search, thanks @florisla

**v1.0.0**
- Fix the spurious newline that bump2version adds when writing to bumpversion.cfg, thanks @kyluca #58
- Add Python3.8 support, thanks @florisla
- Drop Python2 support, thanks @hugovk
- Allow additional arguments to the commit call, thanks @lubomir
- Various documentation improvements, thanks @lubomir @florisla @padamstx @glotis
- Housekeeping, move changelog into own file

**v0.5.11**

- Housekeeping, also publish an sdist
- Housekeeping, fix appveyor builds
- Housekeeping, `make lint` now lints with pylint
- Drop support for Python3.4, thanks @hugovk #79
- Enhance missing VCS command detection (errno 13), thanks @lowell80 #75
- Add environment variables for other scripts to use, thanks @mauvilsa #70
- Refactor, cli.main is now much more readable, thanks @florisla #68
- Fix, retain file newlines for Windows, thanks @hesstobi #59
- Add support (tests) for Pythno3.7, thanks @florisla #49
- Allow any part to be configured in configurable strings such as tag_name etc., thanks @florisla #41

**v0.5.10**

- Housekeeping, use twine

**v0.5.9**

- Fixed windows appveyor-based testing, thanks: @jeremycarroll #33 and #34
- Fixed interpolating correctly when using setup.cfg for config, thanks: @SethMMorton #32
- Improve tox/travis testing, thanks: @ekohl #27
- Fixed markdown formatting in setup.py for pypi.org documentation, thanks: @florisla, @Mattwmaster58 #26

**v0.5.8**

- Updated the readme to markdown for easier maintainability
- Fixed travis testing, thanks: @sharksforarms #15
- Added support for newlines, thanks: @sharksforarms #14
- Fixed an issue with a TypeError on Windows, thanks: @lorengordon #12
- Standardised the python versions, thanks: @ekohl #8
- Fixed testing for pypy, #7

**v0.5.7**

- Added support for signing tags (git tag -s)
  thanks: @Californian [#6](https://github.com/c4urself/bump2version/pull/6)

**v0.5.6**

- Added compatibility with `bumpversion` by making script install as `bumpversion` as well
  thanks: @the-allanc [#2](https://github.com/c4urself/bump2version/pull/2)

**v0.5.5**

- Added support for annotated tags
  thanks: @ekohl @gvangool [#58](https://github.com/peritus/bumpversion/pull/58)

**v0.5.4**

- Renamed to bump2version to ensure no conflicts with original package

**v0.5.3**

- Fix bug where `--new-version` value was not used when config was present
  (thanks @cscetbon @ecordell [#60](https://github.com/peritus/bumpversion/pull/60)
- Preserve case of keys config file
  (thanks theskumar [#75](https://github.com/peritus/bumpversion/pull/75)
- Windows CRLF improvements (thanks @thebjorn)

**v0.5.1**

- Document file specific options `search =` and `replace =` (introduced in 0.5.0)
- Fix parsing individual labels from `serialize =` config even if there are
  characters after the last label (thanks @mskrajnowski [#56](https://github.com/peritus/bumpversion/pull/56)
- Fix: Don't crash in git repositories that have tags that contain hyphens [#51](https://github.com/peritus/bumpversion/pull/51) and [#52](https://github.com/peritus/bumpversion/pull/52)
- Fix: Log actual content of the config file, not what ConfigParser prints
  after reading it.
- Fix: Support multiline values in `search =`
- also load configuration from `setup.cfg`, thanks @t-8ch [#57](https://github.com/peritus/bumpversion/pull/57)

**v0.5.0**

This is a major one, containing two larger features, that require some changes
in the configuration format. This release is fully backwards compatible to
*v0.4.1*, however deprecates two uses that will be removed in a future version.

- New feature: `Part specific configuration`
- New feature: `File specific configuration`
- New feature: parse option can now span multiple line (allows to comment complex
  regular expressions. See re.VERBOSE in the [Python documentation](https://docs.python.org/library/re.html#re.VERBOSE) for details, also see [this testcase](https://github.com/peritus/bumpversion/blob/165e5d8bd308e9b7a1a6d17dba8aec9603f2d063/tests.py#L1202-L1211) as an example.
- New feature: `--allow-dirty` [#42](https://github.com/peritus/bumpversion/pull/42)
- Fix: Save the files in binary mode to avoid mutating newlines (thanks @jaraco [#45](https://github.com/peritus/bumpversion/pull/45)
- License: bumpversion is now licensed under the MIT License [#47](https://github.com/peritus/bumpversion/issues/47)
- Deprecate multiple files on the command line (use a `configuration file` instead, or invoke `bumpversion` multiple times)
- Deprecate 'files =' configuration (use `file specific configuration` instead)

**v0.4.1**

- Add --list option [#39](https://github.com/peritus/bumpversion/issues/39)
- Use temporary files for handing over commit/tag messages to git/hg [#36](https://github.com/peritus/bumpversion/issues/36)
- Fix: don't encode stdout as utf-8 on py3 [#40](https://github.com/peritus/bumpversion/issues/40)
- Fix: logging of content of config file was wrong

**v0.4.0**

- Add --verbose option [#21](https://github.com/peritus/bumpversion/issues/21) [#30](https://github.com/peritus/bumpversion/issues/30)
- Allow option --serialize multiple times

**v0.3.8**

- Fix: --parse/--serialize didn't work from cfg [#34](https://github.com/peritus/bumpversion/issues/34)

**v0.3.7**

- Don't fail if git or hg is not installed (thanks @keimlink)
- "files" option is now optional [#16](https://github.com/peritus/bumpversion/issues/16)
- Fix bug related to dirty work dir [#28](https://github.com/peritus/bumpversion/issues/28)


**v0.3.6**

- Fix --tag default (thanks @keimlink)

**v0.3.5**

- add {now} and {utcnow} to context
- use correct file encoding writing to config file. NOTE: If you are using
  Python2 and want to use UTF-8 encoded characters in your config file, you
  need to update ConfigParser like using 'pip install -U configparser'
- leave `current_version` in config even if available from vcs tags (was
  confusing)
- print own version number in usage
- allow bumping parts that contain non-numerics
- various fixes regarding file encoding

**v0.3.4**

- bugfix: tag_name and message in .bumpversion.cfg didn't have an effect [#9](https://github.com/peritus/bumpversion/issues/9)

**v0.3.3**

- add --tag-name option
- now works on Python 3.2, 3.3 and PyPy

**v0.3.2**

- bugfix: Read only tags from `git describe` that look like versions

**v0.3.1**

- bugfix: `--help` in git workdir raising AssertionError
- bugfix: fail earlier if one of files does not exist
- bugfix: `commit = True` / `tag = True` in .bumpversion.cfg had no effect

**v0.3.0**

- **BREAKING CHANGE** The `--bump` argument was removed, this is now the first
  positional argument.
  If you used `bumpversion --bump major` before, you can use
  `bumpversion major` now.
  If you used `bumpversion` without arguments before, you now
  need to specify the part (previous default was `patch`) as in
  `bumpversion patch`).

**v0.2.2**

- add --no-commit, --no-tag

**v0.2.1**

- If available, use git to learn about current version

**v0.2.0**

- Mercurial support

**v0.1.1**

- Only create a tag when it's requested (thanks @gvangool)

**v0.1.0**

- Initial public version
