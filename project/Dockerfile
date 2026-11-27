# SEA:ME 2.0 drone track - ROS 2 Jazzy dev container (Ubuntu 24.04)
FROM ros:jazzy

ARG USERNAME=dev
ARG HOST_UID=1000
ARG HOST_GID=1000

ENV DEBIAN_FRONTEND=noninteractive

# All apt packages in one place. Add new ones here, not with apt inside the running container.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-dev-tools \
      ros-jazzy-demo-nodes-cpp \
      ros-jazzy-demo-nodes-py \
      ros-jazzy-ros-gz \
      ros-jazzy-turtlesim \
      ros-jazzy-rqt-graph \
      ros-jazzy-teleop-twist-keyboard \
      ros-jazzy-joy \
      ros-jazzy-image-transport-plugins \
      ros-jazzy-usb-cam ros-jazzy-v4l2-camera ros-jazzy-image-transport \
      ros-jazzy-image-view \
      ros-jazzy-cv-bridge \
      ros-jazzy-camera-calibration \
      ros-jazzy-vision-msgs \
      python3-opencv python3-pip \
      ros-jazzy-image-proc \
      ros-jazzy-rqt-image-view v4l-utils mesa-utils \
      ros-jazzy-tf2-tools \
      ros-jazzy-ament-mypy \
      python3-prometheus-client \
      ros-jazzy-foxglove-bridge \
      sudo bash-completion git vim \
    && rm -rf /var/lib/apt/lists/*

# Replace the image's default 'ubuntu' user with one matching your host UID/GID,
# so files created in the mounted workspace are owned by you, not root.
RUN userdel -r ubuntu 2>/dev/null || true \
    && pip install --break-system-packages "onnxruntime==1.20.1" "numpy<2" \
    && groupadd -f -g ${HOST_GID} ${USERNAME} \
    && useradd -m -u ${HOST_UID} -g ${HOST_GID} -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME}

# Names for your host's GPU and input group numbers (group_add in compose.yaml), so
# `groups` in the container stops printing "cannot find name for group ID". Access
# works by number either way; a number the image already has is left alone.
ARG VIDEO_GID=44
ARG RENDER_GID=993
ARG INPUT_GID=994
RUN for g in video:${VIDEO_GID} render:${RENDER_GID} input:${INPUT_GID}; do \
      getent group "${g#*:}" > /dev/null || groupadd -g "${g#*:}" "host-${g%%:*}"; \
    done

# Runtime dir for Qt (Gazebo GUI); matches XDG_RUNTIME_DIR in compose.yaml.
# Criamos e ajustamos a propriedade da pasta .gz AINDA COMO ROOT, antes de montar o volume.
RUN mkdir -p /tmp/runtime-dev && chmod 700 /tmp/runtime-dev \
    && mkdir -p /home/${USERNAME}/.gz \
    && chown -R ${HOST_UID}:${HOST_GID} /home/${USERNAME}/.gz \
    && chown -R ${HOST_UID}:${HOST_GID} /tmp/runtime-dev

USER ${USERNAME}
WORKDIR /home/${USERNAME}/ros2_ws

RUN echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc \
 && echo '[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash' >> ~/.bashrc \
 && echo 'source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash' >> ~/.bashrc

CMD ["sleep", "infinity"]
