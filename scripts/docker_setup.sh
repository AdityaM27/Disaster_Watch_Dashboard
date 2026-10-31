#!/bin/bash
# ==============================================================================
# DisasterWatch India - Automated Docker Setup & Launch Script
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "======================================================================"
echo "🌍 DisasterWatch India: Docker Deployment & Verification"
echo "======================================================================"

# Step 1: Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "[!] Docker engine is not installed on this system."
    echo "[*] Installing docker.io and docker-compose-v2..."
    sudo apt update
    sudo apt install -y docker.io docker-compose-v2
    sudo usermod -aG docker "$USER"
    echo "[✓] Docker installed successfully."
fi

# Step 2: Ensure Docker service is running
echo "[*] Verifying Docker daemon service..."
if ! sudo systemctl is-active --quiet docker; then
    echo "[*] Starting Docker daemon..."
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Step 3: Stop any conflicting host processes on port 8000 if needed
echo "[*] Checking port 8000 availability..."
HOST_PID=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$HOST_PID" ]; then
    echo "[!] Note: Port 8000 is currently occupied by PID $HOST_PID."
    echo "[*] Stopping existing host server on port 8000 to bind Docker container..."
    kill -9 $HOST_PID 2>/dev/null || sudo kill -9 $HOST_PID 2>/dev/null || true
    sleep 2
fi

# Step 4: Build and launch Docker Compose stack
echo "[*] Building and starting DisasterWatch Docker containers..."
if docker compose version &> /dev/null; then
    DOCKER_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
else
    DOCKER_CMD="sudo docker compose"
fi

$DOCKER_CMD down --remove-orphans 2>/dev/null || true
$DOCKER_CMD up -d --build

echo "======================================================================"
echo "[✓] DisasterWatch India Docker Containers are UP & RUNNING!"
echo "======================================================================"
$DOCKER_CMD ps

echo ""
echo "Waiting for health check..."
sleep 5

echo ""
echo "Testing container health endpoint:"
curl -s http://localhost:8000/api/health | grep -o '"status":"[^"]*"' || echo "Container is initializing..."

echo ""
echo "======================================================================"
echo "🚀 ACCESS LINKS FOR DEMO WITH SIR:"
echo "----------------------------------------------------------------------"
echo "  1. Main Web Dashboard (FastAPI + AI Tab): http://localhost:8000"
echo "  2. Streamlit Analytics Dashboard:         http://localhost:8501"
echo "  3. Interactive API Docs (Swagger):        http://localhost:8000/docs"
echo "======================================================================"
echo "To view live container logs:"
echo "  $DOCKER_CMD logs -f"
echo "To stop containers:"
echo "  $DOCKER_CMD down"
echo "======================================================================"
