# Semantic versioning example

bumpversion flow:

    1.0.0 => 1.0.1-dev1 => 1.0.1-dev2 = > 1.0.1-rc1 => 1.0.1-rc2 => 1.0.1
             patch         build          release      build        release

## Details

Start with an initial release, say `1.0.0`.

1. Create a new release, starting with a development build.

        $ bumpversion patch
        => 1.0.1-dev1

2. Every time you build, bump `build`.

        $ bumpversion build
        => 1.0.1-dev2

3. Go to release candidate by bumping `release`.

        $ bumpversion release
        => 1.0.1-rc1

4. With every new build, bump `build`.

        $ bumpversion build
        => 1.0.1-rc2

4. Finally, bump `release` to generate a final release for the current
   `major` / `minor` / `patch` version.

        $ bumpversion release
        => 1.0.1


## Notes

*  Once the final release has been reached, it is not possible to bump
   the `release` before bumping `patch` again. Trying to bump the release
   while in final release state will issue
   `ValueError: The part has already the maximum value among ['dev', 'rc', 'ga'] and cannot be bumped`.

