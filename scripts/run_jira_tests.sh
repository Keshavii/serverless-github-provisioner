#!/bin/bash
# Run JIRA client unit tests and integration tests
# 
# Usage:
#   ./run_jira_tests.sh              # Run only unit tests
#   ./run_jira_tests.sh ENG-12345    # Run unit tests + integration test with ticket

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "  JIRA Client Test Suite"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo ""
    echo "Please create .env file with JIRA credentials:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your credentials"
    exit 1
fi

# ==============================================================================
# PART 1: Unit Tests
# ==============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  PART 1: Unit Tests (Mocked)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run pytest with coverage
echo "Running unit tests..."
pytest tests/test_jira_client.py -v --tb=short --color=yes

UNIT_TEST_EXIT_CODE=$?

if [ $UNIT_TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Unit tests passed!${NC}"
else
    echo ""
    echo -e "${RED}❌ Unit tests failed!${NC}"
    exit $UNIT_TEST_EXIT_CODE
fi

# ==============================================================================
# PART 2: Integration Tests (Optional)
# ==============================================================================

if [ -n "$1" ]; then
    TICKET_ID="$1"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  PART 2: Integration Test (Real JIRA)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    echo -e "${YELLOW}⚠️  This will fetch real JIRA ticket: ${TICKET_ID}${NC}"
    echo ""

    # Check if USE_CUSTOM_FIELDS is set in .env
    USE_CUSTOM_FIELDS=$(grep "^USE_CUSTOM_FIELDS" .env 2>/dev/null | cut -d'=' -f2)

    if [ "$USE_CUSTOM_FIELDS" = "true" ]; then
        echo -e "${BLUE}ℹ️  Custom field extraction enabled - using test_custom_field_extraction.py${NC}"
        python test_custom_field_extraction.py "$TICKET_ID"
    else
        echo -e "${BLUE}ℹ️  JSON parsing mode - using test_jira_integration.py${NC}"
        python test_jira_integration.py "$TICKET_ID"
    fi

    INTEGRATION_TEST_EXIT_CODE=$?

    if [ $INTEGRATION_TEST_EXIT_CODE -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Integration tests passed!${NC}"
    else
        echo ""
        echo -e "${RED}❌ Integration tests failed!${NC}"
        exit $INTEGRATION_TEST_EXIT_CODE
    fi
else
    echo ""
    echo -e "${YELLOW}ℹ️  Skipping integration tests (no ticket ID provided)${NC}"
    echo ""
    echo "To run integration tests with a real JIRA ticket:"
    echo "  ./run_jira_tests.sh RELB-7386    # For custom field extraction test"
    echo "  ./run_jira_tests.sh ENG-12345    # For JSON parsing test"
fi

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ All tests completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit 0

