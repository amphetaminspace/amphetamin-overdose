#!/bin/bash
# amphetamin_Overdose - Passenger Deployment Script
# Run this on your server after cloning the repository

set -e

echo "============================================"
echo "  amphetamin_Overdose - Passenger Deploy"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root for some operations
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
fi

# 1. Check Python version
echo -e "\n${GREEN}[1/7] Checking Python...${NC}"
if command -v python3.11 &>/dev/null; then
    PYTHON=python3.11
elif command -v python3 &>/dev/null; then
    PYTHON=python3
    PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
    echo -e "${YELLOW}Python 3.11+ recommended. Found: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi
echo "Using: $($PYTHON --version 2>&1)"

# 2. Check PostgreSQL
echo -e "\n${GREEN}[2/7] Checking PostgreSQL...${NC}"
if command -v psql &>/dev/null; then
    echo "PostgreSQL found: $(psql --version)"
else
    echo -e "${YELLOW}PostgreSQL not found. Please install it:${NC}"
    echo "  sudo apt install postgresql postgresql-contrib"
fi

# 3. Check Redis
echo -e "\n${GREEN}[3/7] Checking Redis...${NC}"
if command -v redis-cli &>/dev/null; then
    echo "Redis found: $(redis-cli --version)"
else
    echo -e "${YELLOW}Redis not found. Please install it:${NC}"
    echo "  sudo apt install redis-server"
fi

# 4. Create virtual environment
echo -e "\n${GREEN}[4/7] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi
source venv/bin/activate

# 5. Install dependencies
echo -e "\n${GREEN}[5/7] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed${NC}"

# 6. Setup directories and permissions
echo -e "\n${GREEN}[6/7] Setting up directories...${NC}"
mkdir -p logs models tmp
chmod 755 logs models tmp
echo "Directories created: logs, models, tmp"

# 7. Check/create .env
echo -e "\n${GREEN}[7/7] Checking configuration...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}.env created from template. Please edit it with your API keys:${NC}"
        echo "  nano .env"
    else
        echo -e "${RED}.env.example not found!${NC}"
    fi
else
    echo ".env already exists"
fi

# Summary
echo ""
echo "============================================"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys: nano .env"
echo "  2. Setup PostgreSQL database (see DEPLOY_PASSENGER.md)"
echo "  3. Configure Passenger (see DEPLOY_PASSENGER.md)"
echo "  4. Restart Passenger: touch tmp/restart.txt"
echo ""
echo "Useful commands:"
echo "  - Check status: curl http://localhost/health"
echo "  - View logs: tail -f logs/amphetamin_*.log"
echo "  - Restart: touch tmp/restart.txt"
echo ""
