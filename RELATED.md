# Successor

[Bump-my-version](https://pypi.org/project/bump-my-version/) is the successor to bump2version and its predecessor bumpversion.


# Similar or related tools

* [bumpversion](https://pypi.org/project/bumpversion/) is the original project
  off of which `bump2version` was forked.  We'll be merging
  back with them at some point (issue [#86](https://github.com/c4urself/bump2version/issues/86)).
  
* [tbump](https://github.com/tankerhq/tbump) is a complete rewrite, with a nicer UX and additional features, like running commands (aka hooks) before or after the bump. It only works for Git repos right now.

* [ADVbumpversion](https://github.com/andrivet/advbumpversion) is another fork.
  It offered some features that are now incorporated by its author into `bump2version`. 
  This fork is thus now deprecated, and it recommends to use `bump2version`
  (issue [#121](https://github.com/c4urself/bump2version/issues/121)).

* [zest.releaser](https://pypi.org/project/zest.releaser/) manages
  your Python package releases and keeps the version number in one location.

* [setuptools-scm](https://pypi.org/project/setuptools-scm/) relies on 
  version control tags and the state of your working copy to determine
  the version number.

* [incremental](https://pypi.org/project/incremental/) integrates into
  setuptools and maintains the version number in `_version.py`.

* Invocations [packaging.release](https://invocations.readthedocs.io/en/latest/)
  are a set of tasks for [invoke](https://www.pyinvoke.org/).
  These assume your version is in `_version.py` and you're using
  semantic versioning.

* [python-semantic.release](https://github.com/relekang/python-semantic-release)
  automatically bumps your (semantic) version number based on the 
  types of commits (breaking/new/bugfix) in your source control.
  
* [PyCalVer](https://gitlab.com/mbarkhau/pycalver) is very similar to bump2version, but with support for [calendar based versioning](https://calver.org/).


## Change log building
  
* [towncrier](https://pypi.org/project/towncrier/) assembles a changelog
  file from multiple snippets found in individual (merge) commits.
  
* [releases](https://pypi.org/project/releases/) helps build a Sphinx
  ReStructuredText changelog.
  
* [gitchangelog](https://pypi.org/project/gitchangelog/) searches
  the git commit history to make a configurable changelog file.

## Other similar or related tools

Without having looked at these, you may find these interesting:

* https://github.com/silent-snowman/git_bump_version
* https://pypi.org/project/travis-bump-version/
* https://pypi.org/project/bump/
* https://pypi.org/project/bump-anything/
* https://pypi.org/project/bump-release/
* https://github.com/Yuav/python-package-version
* https://github.com/keleshev/version
* https://pypi.org/project/blurb/
* https://regro.github.io/rever-docs/
* https://pypi.org/project/pbr/
* https://pypi.org/project/bumpver/
* https://pypi.org/project/pyxcute/
* https://pypi.org/project/bumpytrack/
* https://pypi.org/project/bumpr/
* https://pypi.org/project/vbump/
* https://pypi.org/project/pybump/
* https://github.com/michaeljoseph/changes
* https://github.com/kmfarley11/version-checker
