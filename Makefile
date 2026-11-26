
SCRIPTS := project/scripts
COMPOSE := docker compose
SERVICE := dev
in_ws    = $(COMPOSE) exec $(SERVICE) bash -c 'source /opt/ros/jazzy/setup.bash && cd ~/ros2_ws && $(1)'

.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

# ========== dev container ==========
up: ## Write .env and start the dev container (builds the image the first time)
	@$(SCRIPTS)/make-env.sh
	$(COMPOSE) up -d

build: ## Rebuild the image (after changing project/Dockerfile)
	@$(SCRIPTS)/make-env.sh
	$(COMPOSE) build

down: ## Stop and remove the dev container (and monitoring, if running)
	$(COMPOSE) --profile monitoring down

clean-volumes: ## Stop everything and delete the volumes (Gazebo model cache, Prometheus and Grafana data)
	$(COMPOSE) --profile monitoring down -v

logs: ## Follow container logs
	$(COMPOSE) logs -f $(SERVICE)	

shell: up ## Open a bash shell in the container
	$(COMPOSE) exec $(SERVICE) bash

# ========== ROS workspace (project/ros2) ==========

ws: up ## colcon build the ROS workspace (project/ros2/src)
	$(call in_ws,colcon build)

ws-clean: up ## Delete the workspace build/, install/ and log/
	$(call in_ws,rm -rf build install log)
	
# ========== tests (results in project/logs/) ==========

test: up ## All tests (ROS + telemetry), like CI: results in project/logs/tests/
	bash $(SCRIPTS)/run_tests.sh

sim-test: ## Headless Gazebo flight test (nightly): results in project/logs/sim_flight/
	bash $(SCRIPTS)/sim_flight_test.sh

sim-test-sensors: ## Headless Gazebo sensor test: results in project/logs/sim_sensors/
	SUITE=sensors bash $(SCRIPTS)/sim_flight_test.sh

# ========== simulation (Gazebo) ==========

sim-keyboard: ws ## Gazebo + keyboard control (no radio: the drone starts armed)
	bash $(SCRIPTS)/sim_keyboard.sh

sim-joy: ws ## Gazebo + joystick (RadioMaster Pocket over USB)
	bash $(SCRIPTS)/sim_joy.sh

sim-stop: ## Stop every sim process left in the container
	bash $(SCRIPTS)/stop_sim.sh

# ========== monitoring (Prometheus + Grafana, monitoring/) ==========

monitor: ## Prometheus + Grafana: the drone dashboard on http://localhost:3000
	$(COMPOSE) --profile monitoring up -d prometheus grafana
	@echo "Grafana: http://localhost:3000 (view without login; admin/admin to edit)"
	@echo "Data appears while a sim or the drone stack runs (metrics_exporter, port 9105)"

monitor-stop: ## Stop Prometheus and Grafana (their data is kept)
	$(COMPOSE) --profile monitoring rm -sf prometheus grafana

# ========== real drone (laptop on the drone's Wi-Fi) ==========

BENCH := python3 project/telemetry/msp_bench.py

bench: ## Full MSP bench, PROPS OFF: make bench NOTE="where, setup" [ARGS="--serial /dev/ttyUSB0"]
	@test -n "$(NOTE)" || { echo 'Say the conditions: make bench NOTE="bench, Pi USB bridge, radio off"'; exit 2; }
	$(BENCH) --logbook "$(NOTE)" $(ARGS)

wifi-rtt: ## Wi-Fi round trip to the FC: make wifi-rtt NOTE="where, ESP mode" [ARGS="--rtt-count 1000"]
	@test -n "$(NOTE)" || { echo 'Say the conditions: make wifi-rtt NOTE="bench, AP mode, radio on"'; exit 2; }
	$(BENCH) --logbook "$(NOTE)" --logbook-name wifi_rtt --skip sensors,load \
		--rtt-commands API_VERSION --rtt-count 200 --rtt-interval 0.05 --timeout 2 $(ARGS)

capture: ## Record MSP replies for the tests: make capture STATE=flat_still [ARGS="--serial /dev/ttyUSB0"]
	@test -n "$(STATE)" || { echo 'Say the drone state: make capture STATE=flat_still (or tilted, radio_off, flow_moving)'; exit 2; }
	$(BENCH) --capture "$(STATE)" $(ARGS)

# INAV bench runs, PROPS OFF. Interactive: they say what to do with the radio.
# Results in project/logs/measurements/. INSTALL=<path> uses another build in the container.
bench-rc: up ## INAV bench, unarmed: ROS sticks through MSP RC OVERRIDE [INSTALL=...]
	bash $(SCRIPTS)/bench_rc_override.sh

bench-armed: up ## INAV bench, ARMED, PROPS OFF: ROS drives the motors [INSTALL=...]
	bash $(SCRIPTS)/bench_rc_armed.sh

motor-music: up ## PROPS OFF: make motor-music MODE=calibrate | MODE=play SONG=f.rtttl [ARGS=...] [MAP=...]
	@case "$(MODE)" in calibrate) ;; play) test -f "$(SONG)" || { echo 'MODE=play needs SONG=path/song.rtttl'; exit 2; } ;; \
		*) echo 'Say MODE=calibrate or MODE=play SONG=path/song.rtttl'; exit 2 ;; esac
	bash $(SCRIPTS)/motor_music/sing.sh $(MODE) $(if $(filter play,$(MODE)),"$(SONG)") $(ARGS)

.PHONY: help up build down clean-volumes logs shell ws ws-clean test sim-test \
	sim-keyboard sim-joy sim-stop monitor monitor-stop bench wifi-rtt capture \
	bench-rc bench-armed motor-music
