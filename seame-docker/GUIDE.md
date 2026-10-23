# Dev Container Setup · Steps 1 & 2

Goal: everyone on the team runs the same ROS 2 Jazzy environment, whatever their host OS (Ubuntu 22.04–26.04, Arch). The test is the setpoint publisher + watchdog from the crash course.

## 0 · Prerequisites (each host)

- **Docker Engine** with the Compose plugin (`docker compose version` should work).
  - Ubuntu: Docker's official apt repo. Arch: `sudo pacman -S docker docker-compose`.
- **Not Docker Desktop.** On Linux it runs inside a VM, and `network_mode: host` won't reach your real network, which breaks ROS 2 discovery.
- Your user in the `docker` group: `sudo usermod -aG docker $USER`, then log out and back in.
- Daemon running: `sudo systemctl enable --now docker`.

## 1 · Repo layout

```
seame-docker/
├── Dockerfile
├── compose.yaml
├── .env              ← you create this (step 2), don't commit it
├── .env.example
└── ros2_ws/
    └── src/
        ├── drone_basics_py/
        └── drone_basics_cpp/
```

Move (or copy) your existing packages into `ros2_ws/src/`. **Don't** copy `build/`, `install/` or `log/`: they were built for your host's ROS and must be rebuilt inside the container. Add these to `.gitignore`:

```
ros2_ws/build/
ros2_ws/install/
ros2_ws/log/
.env
```

## 2 · Create your `.env`

```bash
cd seame-docker
cp .env.example .env
sed -i "s/^HOST_UID=.*/HOST_UID=$(id -u)/; s/^HOST_GID=.*/HOST_GID=$(id -g)/" .env
```

Set `ROS_DOMAIN_ID` to your team's number. Matching UID/GID means files the container writes in `ros2_ws/` belong to you, not root.

## 3 · Build and start

```bash
docker compose build        # first time: a few minutes
docker compose up -d        # starts the container in the background
docker compose exec dev bash   # a shell inside; repeat in more terminals
```

Inside, the prompt shows `dev@<hostname>`. Check:

```bash
echo $ROS_DISTRO     # jazzy
echo $ROS_DOMAIN_ID  # your team number
```

## 4 · Build the workspace (inside the container)

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

New terminals source it automatically through `.bashrc`.

## 5 · Smoke test

Terminal A (`docker compose exec dev bash`):
```bash
ros2 run drone_basics_py setpoint_pub
```
Terminal B:
```bash
ros2 run drone_basics_cpp watchdog
ros2 topic hz /setpoint_velocity    # third terminal: ~10 Hz
```

**Pass:** Ctrl-C the publisher → the watchdog warns within ~0.6 s. Restart it → "Setpoints are back".

Optional discovery check across two laptops on the same Wi-Fi and the same `ROS_DOMAIN_ID`: `ros2 run demo_nodes_cpp talker` on one, `ros2 run demo_nodes_py listener` on the other.

## 6 · Daily use

| Do | Command |
|---|---|
| Start | `docker compose up -d` |
| Open a shell | `docker compose exec dev bash` |
| Stop | `docker compose down` |
| Rebuild after Dockerfile changes | `docker compose build && docker compose up -d` |

Edit code on the host with your usual editor; the workspace is mounted, so changes appear instantly inside. Python edits are live (`--symlink-install`); C++ needs `colcon build`.

## Step 2 · Team checklist

Each teammate runs sections 0–5 on their own machine and reports back:

| Name | Host OS | Docker version | Build OK | Smoke test OK | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Troubleshooting

- **`permission denied ... docker.sock`**: not in the `docker` group yet, or you didn't log out and back in.
- **Root-owned `build/` or `install/`**: `.env` was missing on build. Fix `.env`, `docker compose build --no-cache`, then `sudo rm -rf ros2_ws/{build,install,log}` and rebuild.
- **`Package 'drone_basics_py' not found`**: `source install/setup.bash`, or open a new shell.
- **Nodes on two machines don't see each other**: same `ROS_DOMAIN_ID`? Firewall (Arch with `ufw`/`firewalld` often blocks UDP multicast)? Test with `ros2 multicast receive` / `ros2 multicast send`. Wi-Fi with client isolation (common on campus networks) blocks discovery entirely.
- **Host ROS (Lyrical) and container ROS (Jazzy) talking to each other**: avoid it. Cross-distro communication often works but isn't guaranteed. Run everything in the container.

Next: Gazebo + GPU passthrough (step 3). After that, [`SIM_TELEOP.md`](SIM_TELEOP.md) covers flying the sim with the keyboard or the RadioMaster Pocket. It needs a container rebuild and `./make-env.sh` again (for `INPUT_GID`).
