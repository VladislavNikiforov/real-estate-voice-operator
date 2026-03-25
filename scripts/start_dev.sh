#!/usr/bin/env bash
# scripts/start_dev.sh — Start server + mock OpenClaw together
set -e

CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}  🚀 Real Estate Voice Operator — Dev Mode${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Activate venv if present
[ -d "venv" ] && source venv/bin/activate

echo "Starting mock OpenClaw on :8888..."
python -m mock.mock_openclaw &
MOCK_PID=$!
sleep 1

echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  NEXT STEPS:"
echo "  1. Open a new terminal and run:  ngrok http 8000"
echo "  2. Copy the https:// ngrok URL"
echo "  3. In Vapi dashboard → Server URL:"
echo "     https://YOUR-NGROK.ngrok.io/api/vapi/tool-call"
echo "  4. Call your Vapi phone number!"
echo ""
echo "  Quick test (no phone needed):"
echo "     python scripts/test_call.py"
echo ""
echo "  Full pipeline test:"
echo "     python scripts/test_full_pipeline.py"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

python main.py

kill $MOCK_PID 2>/dev/null || true
