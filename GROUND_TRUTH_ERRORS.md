# Ground Truth Errors: Progressive Corruption Structure
## errors/ Folder Analysis

**Date**: 2026-03-07
**Structure**: Progressive error accumulation (1.txt = 1 error, 10.txt = 10 cumulative errors)

---

## Smartphone Errors (Nova X5)

### Error Catalog:

| # | Error | Incorrect Value | Correct Value | Type |
|---|-------|----------------|---------------|------|
| **1** | Display size | 6.5" | 6.3" | Numerical |
| **2** | Main camera | 48 MP | 50 MP | Numerical |
| **3** | Storage options | 1TB option | Max 512 GB | Feature hallucination |
| **4** | RAM configurations | 16 GB option | Max 12 GB | Feature hallucination |
| **5** | Wi-Fi support | Wi-Fi 7 | Wi-Fi 6/6E | Feature hallucination |
| **6** | Wireless charging | 10W Qi wireless | Not supported | Feature hallucination |
| **7** | Security feature | Hourly antivirus | Not mentioned | Feature hallucination |
| **8** | AI capability | Offline AI video rendering | Not supported | Feature hallucination |
| **9** | Fast charging | 60W USB-C | 30-45W | Numerical |
| **10** | Storage expansion | External SSD via SIM tray | Not supported | Feature hallucination |

---

## Melatonin Errors

| # | Error | Incorrect Value | Correct Value | Type |
|---|-------|----------------|---------------|------|
| **1** | Dosage per tablet | 5 mg | 3 mg | Numerical |
| **2** | Bottle count | 100 tablets | 60 tablets | Factual |
| **3** | Vegan claim | Vegan + fish-derived | Vegan only | Logical contradiction |
| **4** | Allergen claim | 0mg gluten + wheat traces | No wheat | Logical contradiction |
| **5** | Lead limit | <5 ppm | <0.5 mcg/serving | Numerical |
| **6** | Storage temp | Exactly 0°C | 15-30°C | Logical |
| **7** | Dosing frequency | Every 2 hours | Before bed | Factual |
| **8** | FDA approval | FDA approved | Not FDA approved | Factual |
| **9** | Age restriction | Avoid if over 18 | If under 18 consult | Factual |
| **10** | Side effect | Permanent drowsiness | Temporary | Factual |

---

## CoreCoin/Crypto Errors

| # | Error | Incorrect Value | Correct Value | Type |
|---|-------|----------------|---------------|------|
| **1** | Block time | ~4 seconds | ~5 seconds | Numerical |
| **2** | Light validators | Don't stake | Must stake | Logical |
| **3** | Trading pauses | Regional maintenance | 24/7 trading | Feature hallucination |
| **4** | Key backup | Automatic key-sharding | Manual backup | Feature hallucination |
| **5** | Smart contracts | Gas-free execution | Gas fees required | Factual |
| **6** | Governance | Auto-pass without quorum | Requires quorum | Logical |
| **7** | Cross-chain | RPC simulate cross-chain | Not supported | Feature hallucination |
| **8** | Unstaking penalty | Reduces historical rewards | Standard rules | Factual |
| **9** | Validator inactivity | Locks governance rights | Standard rules | Factual |
| **10** | Staking tiers | Region-based fixed rates | Performance-based | Factual |

---

**Total**: 30 errors (10 per product)
**Structure**: Files 1-10 with cumulative errors
