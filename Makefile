D       := seame-docker
COMPOSE := docker compose -f $(D)/compose.yaml
SERVICE := dev

.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

up: ## Write .env and start the dev container (builds the image the first time)
	$(D)/scripts/make-env.sh
	$(COMPOSE) up -d

build: ## Rebuild the image (after changing the Dockerfile)
	$(COMPOSE) build

down: ## Stop and remove the dev container
	$(COMPOSE) down

clean-volumes: ## Stop the container and delete its volumes (Gazebo model cache)
	$(COMPOSE) down -v

logs: ## Follow container logs
	$(COMPOSE) logs -f $(SERVICE)

shell: up ## Open a bash shell in the container
	$(COMPOSE) exec $(SERVICE) bash

smoke: up ## Smoke test (publishers and watchdog)
	bash $(D)/scripts/smoke_test.sh

sim-keyboard: up ## Gazebo + keyboard control
	bash $(D)/scripts/sim_keyboard.sh

sim-joy: up ## Gazebo + joystick (RadioMaster)
	bash $(D)/scripts/sim_joy.sh

.PHONY: help up build down clean-volumes logs shell smoke sim-keyboard sim-joy
