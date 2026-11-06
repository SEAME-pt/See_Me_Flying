#!/usr/bin/env bash
# Creates .env for the SEA:ME dev container from your host's user/group IDs.
set -euo pipefail

# Always write .env next to compose.yaml, wherever the script is called from.
cd "$(dirname "$0")/.."

if [[ $EUID -eq 0 ]]; then
  echo "Don't run this with sudo: it would record root's IDs (0) instead of yours." >&2
  exit 1
fi

domain=42 # default ROS domain ID at the moment, 
# chose another one to avoid future conflicts with the other teams

if [[ -f .env ]]; then
  read -rp ".env already exists. Overwrite? [y/N]: " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { echo "Left .env unchanged."; exit 0; }
fi

# GPU groups: the container's dev user needs these to open /dev/dri.

# Missing group -> line left out -> compose.yaml falls back to its default.
gid_of() { getent group "$1" 2>/dev/null | cut -d: -f3 || true; }

video_gid="$(gid_of video)"
render_gid="$(gid_of render)"
input_gid="$(gid_of input)"

cat > .env << ENV

HOST_UID=$(id -u)
HOST_GID=$(id -g)
ROS_DOMAIN_ID=$domain
ENV
[[ -n "$video_gid"  ]] && echo "VIDEO_GID=$video_gid"   >> .env
[[ -n "$render_gid" ]] && echo "RENDER_GID=$render_gid" >> .env
[[ -n "$input_gid"  ]] && echo "INPUT_GID=$input_gid"   >> .env
[[ -z "$video_gid$render_gid" ]] && echo "${YELLOW}Note: no video/render groups found; Gazebo will use software rendering.${DEFAULT}" >&2
# echo "Wrote .env:"
# grep -v '^#' .env
# echo
# echo "Next: docker compose build && docker compose up -d"
