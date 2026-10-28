#!/bin/bash
set -e

if [ "$(docker compose ps -q --status running dev)" ]; then
    echo -e "🟢 The container is already running.\n"
else
    if [ ! -f .env ]; then
        echo "⚙️ Generating .env file automatically..."
        if [ -f ./scripts/make-env.sh ]; then
            ./scripts/make-env.sh 42
        else
            cp .env.example .env
            sed -i "s/^HOST_UID=.*/HOST_UID=$(id -u)/; s/^HOST_GID=.*/HOST_GID=$(id -g)/" .env
        fi
    fi

    docker compose up -d
fi

echo "========================================="
echo "   🚁 SEA:ME ROS 2 - Dev Environment     "
echo -e "=========================================\n"
PS3="Select the environment/test option (1-5): "

options=(
    "Smoke Test (Publishers & Watchdog)"
    "Gazebo + ROS 2 (Keyboard Control)"
    "Gazebo + ROS 2 (RadioMaster / Joystick)"
    "Interactive Shell (Container Bash)"
    "Exit"
)

select opt in "${options[@]}"; do
    case $opt in
        "Smoke Test (Publishers & Watchdog)")
            echo -e "\n🔥 Launching Smoke Test..."
            bash scripts/smoke_test.sh 
            break
            ;;
        "Gazebo + ROS 2 (Keyboard Control)")
            echo -e "\n🎮 Launching Gazebo with Keyboard Control..."
            bash scripts/sim_keyboard.sh
            break
            ;;
        "Gazebo + ROS 2 (RadioMaster / Joystick)")
            echo -e "\n📻 Launching Gazebo with Joystick Control..."
            bash scripts/sim_joy.sh
            break
            ;;
        "Interactive Shell (Container Bash)")
            echo -e "\n💻 Opening interactive shell..."
            docker compose exec dev bash
            break
            ;;
        "Exit")
            echo "Exiting..."
            exit 0
            ;;
        *) 
            echo "Invalid option: $REPLY. Choose a number between 1 and 5."
            ;;
    esac
done