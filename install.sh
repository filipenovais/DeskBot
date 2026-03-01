#!/bin/bash

# DeskBot Installation Script
# Usage: ./install.sh [--ollama]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_OLLAMA=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
if [[ "$1" == "--ollama" ]]; then
    INSTALL_OLLAMA=true
fi

echo "=================================="
echo "DeskBot Installation"
echo "=================================="
echo ""

# Function to print colored messages
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Check if conda (miniconda/anaconda) is installed
print_info "Checking for Conda installation..."
if ! command -v conda &> /dev/null; then
    print_error "Conda (Miniconda/Anaconda) is not installed!"
    echo ""
    echo "Please install Miniconda or Anaconda from:"
    echo "  Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    echo "  Anaconda: https://www.anaconda.com/download"
    echo ""
    exit 1
fi
CONDA_VERSION=$(conda --version 2>&1)
print_success "Found: $CONDA_VERSION"

# Check if Docker is installed
print_info "Checking for Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    echo ""
    echo "Please install Docker from:"
    echo "  https://docs.docker.com/get-docker/"
    echo ""
    exit 1
fi
DOCKER_VERSION=$(docker --version 2>&1)
print_success "Found: $DOCKER_VERSION"

# Check if docker-compose is installed
print_info "Checking for Docker Compose installation..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed!"
    echo ""
    echo "Please install Docker Compose from:"
    echo "  https://docs.docker.com/compose/install/"
    echo ""
    exit 1
fi
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version 2>&1)
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_VERSION=$(docker compose version 2>&1)
    COMPOSE_CMD="docker compose"
fi
print_success "Found: $COMPOSE_VERSION"

echo ""
echo "All prerequisites are satisfied!"
echo ""

# Start Docker services
print_info "Starting database-service with Docker..."
cd "$SCRIPT_DIR/database-service"
$COMPOSE_CMD up -d --build
if [ $? -eq 0 ]; then
    print_success "Database service is running on port 8000"
else
    print_error "Failed to start database service"
    exit 1
fi

# Start Ollama service if flag is set
if [ "$INSTALL_OLLAMA" = true ]; then
    print_info "Starting ollama-service with Docker..."
    cd "$SCRIPT_DIR/ollama-service"
    $COMPOSE_CMD up -d --build
    if [ $? -eq 0 ]; then
        print_success "Ollama service is running on port 11434"
    else
        print_error "Failed to start ollama service"
        exit 1
    fi
fi

# Return to script directory
cd "$SCRIPT_DIR"

# Create/update Conda environment
print_info "Setting up Conda environment from environment.yml..."
if conda env list | grep -q "^deskbot_env "; then
    print_info "Environment 'deskbot_env' already exists. Updating..."
    conda env update -n deskbot_env -f environment.yml --prune
else
    print_info "Creating new environment 'deskbot_env'..."
    conda env create -f environment.yml
fi

if [ $? -eq 0 ]; then
    print_success "Conda environment 'deskbot_env' is ready"
else
    print_error "Failed to create/update Conda environment"
    exit 1
fi

echo ""
echo "=================================="
print_success "Installation completed successfully!"
echo "=================================="
echo ""
echo "Services running:"
echo "  - Database service: http://localhost:8000"
if [ "$INSTALL_OLLAMA" = true ]; then
    echo "  - Ollama service: http://localhost:11434"
fi
echo ""
echo "To start the application:"
echo "  conda activate deskbot_env && python run.py"
echo ""
echo "To stop Docker services:"
echo "  cd database-service && $COMPOSE_CMD down"
if [ "$INSTALL_OLLAMA" = true ]; then
    echo "  cd ollama-service && $COMPOSE_CMD down"
fi
echo ""
