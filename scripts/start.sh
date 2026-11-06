#!/bin/bash

PINK = "\033]01;31\]" 
DEFAULT = "\033]00m\]"   
BOLD_GREEN = "\033]01;36\]" 
GREEN = "\033]02;36\]" 
BLUE = "\033]01;34\]" 
BOLD_YELLOW = "\033]01;33\]" 
YELLOW = "\033]02;33\]" 


set -euo pipefail

if [ "$(docker compose ps -q --status running dev)" ]; then
    echo -e "${GREEN}The container is already running.\n${DEFAULT}
    echo -e "${BOLD_YELLOW}You can attach to the container using:\n${DEFAULT}
    echo -e "${BLUE}docker compose exec dev bash\n${DEFAULT}
else
    if [ ! -f .env ]; then
        echo -e "${GREEN}Generating .env file...${DEFAULT}"
        ./scripts/make-env.sh
    fi
fi
