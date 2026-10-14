# SEA:ME 2.0 drone track - ROS 2 Jazzy dev container (Ubuntu 24.04)
FROM ros:jazzy

ARG USERNAME=dev
ARG HOST_UID=1000
ARG HOST_GID=1000

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-dev-tools \
      ros-jazzy-demo-nodes-cpp \
      ros-jazzy-demo-nodes-py \
      sudo bash-completion git vim \
    && rm -rf /var/lib/apt/lists/*

# Replace the image's default 'ubuntu' user with one matching your host UID/GID,
# so files created in the mounted workspace are owned by you, not root.
RUN userdel -r ubuntu 2>/dev/null || true \
    && groupadd -f -g ${HOST_GID} ${USERNAME} \
    && useradd -m -u ${HOST_UID} -g ${HOST_GID} -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME}

USER ${USERNAME}
WORKDIR /home/${USERNAME}/ros2_ws

RUN echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc \
 && echo '[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash' >> ~/.bashrc \
 && echo 'source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash' >> ~/.bashrc

CMD ["sleep", "infinity"]
