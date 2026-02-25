#!/bin/bash

# ==============================================================================
# OSINT PLATFORM - ULTIMATE SYSTEM DOCTOR & VALIDATION SCRIPT
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}        OSINT PLATFORM - ADVANCED ENVIRONMENT DOCTOR        ${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

FAILURES=0
WARNINGS=0

# --- Helper Functions ---
pass() { echo -e "  [${GREEN}PASS${NC}] $1"; }
fail() { echo -e "  [${RED}FAIL${NC}] $1"; ((FAILURES++)); }
warn() { echo -e "  [${YELLOW}WARN${NC}] $1"; ((WARNINGS++)); }

# ------------------------------------------------------------------------------
# 1. HARDWARE & SYSTEM RESOURCES
# ------------------------------------------------------------------------------
echo -e "🖥️  ${YELLOW}Checking System Resources...${NC}"

# Check RAM (Minimum 8GB recommended for Neo4j + AI workers)
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -ge 7500 ]; then
    pass "System RAM: ${TOTAL_RAM}MB (Sufficient)"
else
    warn "System RAM: ${TOTAL_RAM}MB (Less than 8GB recommended. Processing may be slow)"
fi

# Check Disk Space (Minimum 20GB free recommended)
FREE_DISK=$(df -m / | awk 'NR==2 {print $4}')
if [ "$FREE_DISK" -ge 20480 ]; then
    pass "Free Disk Space: $((FREE_DISK/1024))GB (Sufficient)"
else
    warn "Free Disk Space: $((FREE_DISK/1024))GB (Less than 20GB free. DBs might fill up fast)"
fi

# Check GPU capability (Required for optimal OCR/Local LLM)
if command -v nvidia-smi &> /dev/null; then
    pass "NVIDIA GPU Detected (Hardware acceleration available)"
else
    warn "nvidia-smi not found. Worker will fall back to CPU, which is significantly slower."
fi

# ------------------------------------------------------------------------------
# 2. REQUIRED DEPENDENCIES
# ------------------------------------------------------------------------------
echo ""
echo -e "📦 ${YELLOW}Checking Core Dependencies...${NC}"

for cmd in docker make uv; do
    if command -v $cmd &> /dev/null; then
        pass "'$cmd' is installed."
    else
        fail "'$cmd' is missing! Please install it."
    fi
done

if docker compose version &> /dev/null; then
    pass "'docker compose' plugin is installed."
else
    fail "'docker compose' is missing! Please install Docker Compose V2."
fi

# ------------------------------------------------------------------------------
# 3. PORT CONFLICT SCANNER
# ------------------------------------------------------------------------------
echo ""
echo -e "🔌 ${YELLOW}Scanning Network Ports...${NC}"

check_port() {
    PORT=$1
    SERVICE=$2
    if ss -tuln | grep -q ":$PORT "; then
        fail "Port $PORT ($SERVICE) is ALREADY IN USE by a host process!"
    else
        pass "Port $PORT ($SERVICE) is free."
    fi
}

check_port 3000 "Frontend"
check_port 6379 "Redis"
check_port 7474 "Neo4j HTTP"
check_port 7687 "Neo4j Bolt"
check_port 8000 "API / ChromaDB"

# ------------------------------------------------------------------------------
# 4. ENVIRONMENT & SECRETS VALIDATION
# ------------------------------------------------------------------------------
echo ""
echo -e "🔐 ${YELLOW}Validating Environment (.env)...${NC}"

if [ -f ".env" ]; then
    pass ".env file exists."
    
    # Check for default placeholders
    if grep -q "your_actual_api_key_here" ".env" || grep -q "sk-or-v1-placeholder" ".env"; then
        fail "OPENROUTER_API_KEY is still set to a placeholder!"
    else
        pass "OpenRouter API Key looks customized."
    fi
    
    if grep -q "NEO4J_PASSWORD=password" ".env"; then
        warn "Neo4j is using the default 'password'. Consider changing this for production."
    else
        pass "Neo4j credentials customized."
    fi
else
    fail "Missing .env file in root directory!"
fi

# ------------------------------------------------------------------------------
# 5. OUTBOUND NETWORK CONNECTIVITY
# ------------------------------------------------------------------------------
echo ""
echo -e "🌐 ${YELLOW}Testing External Connectivity...${NC}"

if curl -s --connect-timeout 5 https://openrouter.ai/api/v1/auth/key > /dev/null; then
    pass "Can successfully reach OpenRouter.ai API endpoints."
else
    warn "Cannot ping OpenRouter.ai. You might have outbound DNS or firewall issues."
fi

# ------------------------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}============================================================${NC}"
if [ $FAILURES -gt 0 ]; then
    echo -e "RESULT: ❌ ${RED}FOUND $FAILURES FATAL ERRORS.${NC} DO NOT LAUNCH YET."
    echo -e "Please fix the red items above."
elif [ $WARNINGS -gt 0 ]; then
    echo -e "RESULT: ⚠️  ${YELLOW}SYSTEM READY, BUT HAS $WARNINGS WARNINGS.${NC}"
    echo -e "You can launch, but be aware of the yellow warnings."
else
    echo -e "RESULT: ✅ ${GREEN}SYSTEM IS FLAWLESS. READY FOR LAUNCH.${NC}"
fi
echo -e "${BLUE}============================================================${NC}"
