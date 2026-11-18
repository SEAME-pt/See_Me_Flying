# Using the Makefile

Run everything from the repo root. `make` lists all commands.

## Start

```bash
make up      # start the container (first time: builds the image)
make ws      # build the ROS code
```

## Simulation

```bash
make sim-keyboard   # Gazebo + keyboard
make sim-joy        # Gazebo + RadioMaster
make sim-stop       # stop the sim
```

## Tests

```bash
make test       # all tests (~2 min)
make sim-test   # full Gazebo flight (~2 min)
```

Results go to `project/logs/`.

## Other

```bash
make shell      # terminal inside the container
make down       # stop the container
make build      # rebuild the image after changing project/Dockerfile
make ws-clean   # delete the build, then run make ws
```

## Problems

- **"seame-dev is already in use"**: another copy of the repo has its container running. Run `docker rm -f seame-dev`.
- **"Gazebo is already running"**: `make sim-stop`
- **"Package not found"**: `make ws`
