#!/bin/bash
# Verification script to check if server is ready for glass box audit analysis

echo "============================================"
echo "Glass Box Audit - Readiness Check"
echo "============================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES=0

# 1. Check if experiments.csv exists
echo "1. Checking experiments.csv..."
if [ -f "results/experiments.csv" ]; then
    LINES=$(wc -l < results/experiments.csv)
    if [ "$LINES" -ge 1620 ]; then
        echo -e "${GREEN}✓${NC} experiments.csv exists ($LINES lines)"
    else
        echo -e "${YELLOW}⚠${NC} experiments.csv exists but only $LINES lines (expected 1621)"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}✗${NC} experiments.csv NOT FOUND"
    echo "  Location: results/experiments.csv"
    echo "  Action: Upload from local machine"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 2. Check if outputs directory exists and has files
echo "2. Checking outputs directory..."
if [ -d "outputs" ]; then
    FILE_COUNT=$(ls -1 outputs/*.txt 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -ge 1500 ]; then
        echo -e "${GREEN}✓${NC} outputs/ directory exists ($FILE_COUNT .txt files)"
    elif [ "$FILE_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC} outputs/ has only $FILE_COUNT files (expected ~1620)"
        ISSUES=$((ISSUES + 1))
    else
        echo -e "${RED}✗${NC} outputs/ directory is empty"
        echo "  Action: Upload generated materials or re-run generation"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}✗${NC} outputs/ directory NOT FOUND"
    echo "  Action: Create directory and upload generated materials"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 3. Check if product YAMLs exist
echo "3. Checking product YAMLs..."
YAML_COUNT=0
for product in supplement_melatonin smartphone_mid cryptocurrency_corecoin; do
    if [ -f "products/${product}.yaml" ]; then
        YAML_COUNT=$((YAML_COUNT + 1))
    fi
done

if [ "$YAML_COUNT" -eq 3 ]; then
    echo -e "${GREEN}✓${NC} All 3 product YAMLs found"
else
    echo -e "${YELLOW}⚠${NC} Only $YAML_COUNT/3 product YAMLs found"
    echo "  Expected: products/supplement_melatonin.yaml"
    echo "           products/smartphone_mid.yaml"
    echo "           products/cryptocurrency_corecoin.yaml"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 4. Check if .env exists and has ANTHROPIC_API_KEY
echo "4. Checking environment variables..."
if [ -f ".env" ]; then
    if grep -q "ANTHROPIC_API_KEY" .env; then
        KEY_VALUE=$(grep "ANTHROPIC_API_KEY" .env | cut -d '=' -f2)
        if [ -n "$KEY_VALUE" ] && [ "$KEY_VALUE" != "your_key_here" ]; then
            echo -e "${GREEN}✓${NC} ANTHROPIC_API_KEY is set in .env"
        else
            echo -e "${RED}✗${NC} ANTHROPIC_API_KEY is empty or placeholder"
            echo "  Action: Set real API key in .env"
            ISSUES=$((ISSUES + 1))
        fi
    else
        echo -e "${RED}✗${NC} ANTHROPIC_API_KEY not found in .env"
        echo "  Action: Add ANTHROPIC_API_KEY=your_key_here to .env"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}✗${NC} .env file NOT FOUND"
    echo "  Action: Create .env with API keys"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 5. Check if Python dependencies are installed
echo "5. Checking Python dependencies..."
if command -v python3 &> /dev/null; then
    # Check anthropic package
    if python3 -c "import anthropic" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} anthropic package installed"
    else
        echo -e "${RED}✗${NC} anthropic package NOT installed"
        echo "  Action: pip install anthropic"
        ISSUES=$((ISSUES + 1))
    fi

    # Check transformers package
    if python3 -c "import transformers" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} transformers package installed"
    else
        echo -e "${RED}✗${NC} transformers package NOT installed"
        echo "  Action: pip install transformers torch"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}✗${NC} python3 not found"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 6. Check if glass_box_audit.py has Claude support
echo "6. Checking glass_box_audit.py..."
if [ -f "analysis/glass_box_audit.py" ]; then
    if grep -q "CLAUDE_MODEL" analysis/glass_box_audit.py; then
        echo -e "${GREEN}✓${NC} glass_box_audit.py has Claude explainer support"
    else
        echo -e "${RED}✗${NC} glass_box_audit.py missing Claude support"
        echo "  Action: Git pull failed? Re-pull from main"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}✗${NC} analysis/glass_box_audit.py NOT FOUND"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# Summary
echo "============================================"
echo "SUMMARY"
echo "============================================"
if [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "You are ready to run analysis:"
    echo ""
    echo "  # Without Claude (faster, cheaper)"
    echo "  python analysis/glass_box_audit.py --limit 1620 --resume"
    echo ""
    echo "  # With Claude explanations (recommended)"
    echo "  python analysis/glass_box_audit.py --limit 1620 --use-claude-explainer --resume"
    echo ""
    echo "  # With semantic filter + Claude (best quality)"
    echo "  python analysis/glass_box_audit.py --limit 1620 --use-semantic-filter --use-claude-explainer --resume"
else
    echo -e "${RED}✗ FOUND $ISSUES ISSUE(S)${NC}"
    echo ""
    echo "Please fix the issues above before running analysis."
    echo ""
    echo "Common fixes:"
    echo "  1. Upload experiments.csv: scp results/experiments.csv server:/path/to/llm_research_app/results/"
    echo "  2. Upload outputs: scp -r outputs/ server:/path/to/llm_research_app/"
    echo "  3. Install packages: pip install -r requirements.txt"
    echo "  4. Set API key: echo 'ANTHROPIC_API_KEY=your_key' >> .env"
fi
echo "============================================"

exit $ISSUES
