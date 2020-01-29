# Similar or related tools

* [bumpversion](https://pypi.org/project/bumpversion/) is the original project
  off of which `bump2version` was forked.  We'll be merging
  back with them at some point (issue [#86](https://github.com/c4urself/bump2version/issues/86)).

* [ADVbumpversion](https://github.com/andrivet/advbumpversion) is another fork.
  It offers some features which are still work in progress here; it's
  definitely our desire to merge back (issue [#121](https://github.com/c4urself/bump2version/issues/121)).

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
  
  
## Change log building
  
* [towncrier](https://pypi.org/project/towncrier/) assembles a changelog
  file from multiple snippets found in individual (merge) commits.
  
* [releases](https://pypi.org/project/releases/) helps build a Sphinx
  ReStructuredText changelog.
  
* [gitchangelog](https://pypi.org/project/gitchangelog/) searches
  the git commit history to make a configurable changelog file.
