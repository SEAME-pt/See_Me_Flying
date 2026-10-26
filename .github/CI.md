# CI (Continuous Integration)

Every push or pull request to `main` or `test` is checked automatically on GitHub. The workflow is [`workflows/ci.yml`](workflows/ci.yml).

## What it checks

That the ROS 2 workspace in `seame-docker/ros2_ws` **builds and passes its tests on a clean machine**. It does not run the simulation.

It runs inside the plain `ros:jazzy` image, not our dev image, so it also catches dependencies that are installed in the Dockerfile but missing from a `package.xml`.

## Steps

| Step | What it does |
| --- | --- |
| Check out code | Downloads the repo |
| Install dependencies | `rosdep install` reads each `package.xml` and installs what it lists, including `<test_depend>` |
| Build | `colcon build` for all packages in `src/` |
| Test | `colcon test`, then `colcon test-result --verbose`; fails if any test fails |

The job is stopped after 60 minutes if it hangs.

## Where the tests come from

`ci.yml` does not define tests; it runs whatever the packages define:

- **C++ / CMake packages:** `ament_lint_auto` in `CMakeLists.txt` (under `if(BUILD_TESTING)`) runs the standard linters: uncrustify (C++ format), cppcheck, flake8, pep257, lint_cmake, xmllint.
- **Python packages:** the files in `<package>/test/` (`test_flake8.py`, `test_mypy.py`, ...).

Most failures are code style, not bugs. The log names the file and line.

## Run it locally before pushing

Inside the dev container (`docker compose exec dev bash`):

```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -y   # once, installs test tools
rm -rf build install log                          # clean build, like CI
colcon build
colcon test && colcon test-result --verbose
```

`colcon test-result` should report `0 errors, 0 failures`.

Fix C++ formatting automatically:

```bash
ament_uncrustify --reformat src/<package>
```

## Checking results on GitHub

Open the repo's **Actions** tab, or click the ✔ / ✖ next to a commit. Expand the failed step to see the log.
