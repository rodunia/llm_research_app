#!/bin/bash
# Find all 10 intentional errors in CoreCoin output files

echo "=== CoreCoin Intentional Errors - Location Report ==="
echo ""

echo "Error 1: Block time 4s (should be 5s)"
grep -n "4 second" outputs/1.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 2: Light validators (non-staking)"
grep -n "light.*validator\|validator.*light" outputs/2.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 3: Regional trading pauses"
grep -n "trading.*pause\|pause.*trading\|regional.*trading" outputs/3.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 4: Automatic key sharding"
grep -n "shard\|sharding.*key\|automatic.*backup" outputs/4.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 5: EVM without gas fees"
grep -n "without.*gas\|gas.*free\|no.*gas" outputs/5.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 6: Auto-pass without quorum"
grep -n "quorum\|auto.*pass\|automatic.*approval" outputs/6.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 7: RPC cross-chain simulation"
grep -n "RPC\|cross.*chain.*simul" outputs/7.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 8: Unstaking reduces historical rewards"
grep -n "unstaking\|historical.*reward" outputs/8.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 9: Validator inactivity locks governance"
grep -n "inactivity.*lock\|lock.*governance" outputs/9.txt 2>/dev/null | head -1 || echo "NOT FOUND"
echo ""

echo "Error 10: Region-based staking tiers"
grep -n "region.*staking\|staking.*tier\|fixed.*rate.*region" outputs/10.txt 2>/dev/null | head -1 || echo "NOT FOUND"
