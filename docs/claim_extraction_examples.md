# Claim Extraction Examples

Real examples from the LLM research pipeline, showing structure-aware claim extraction (v2.0).

**All excerpts below are verbatim segments of model-generated outputs (not prompts).**  
Claims are exact substrings; offsets are shown for traceability.

**Features demonstrated:**
- Block-aware parsing (headlines, Q/A, disclaimers)
- Claim kind tagging (product_claim vs disclaimer)
- Anchor-based trigger detection (numeric, guarantee, medical, financial, comparative)
- Exact char_span offsets (all sentences are verifiable substrings)

---

## Example 1 — Digital Ad
**Run ID:** `digital_ad`  
**Product:** unknown | **Engine:** unknown  
**Extractor:** v2.0

### Generated Text Excerpt (Verbatim Model Output)

```
Experience the Nova X5 5G Smartphone with a stunning 6.5 in 120 Hz display, 5000 mAh battery, and lightning-fast 30 W USB-C charging. Enjoy 5G connectivity, Wi-Fi 6, and Bluetooth 5.3 support. 

Learn more.  

Disclaimers:  
Network availability (including 5G) depends on carrier and coverage; speeds vary.  
Actual battery life varies by usage, settings, and network conditions.  
Avoid liquid exposure; no water-resistance certification is claimed.
```

### Extracted Claims (Verbatim)

| Claim ID | Claim Kind | Block Kind | Triggers | Char Span | Sentence |
|----------|------------|------------|----------|-----------|----------|
| `digital_ad::sent000...` | product_claim | unknown | numeric | (0, 133) | Experience the Nova X5 5G Smartphone with a stunning 6.5 in 120 Hz display, 5000... |
| `digital_ad::sent001...` | product_claim | unknown | numeric | (134, 192) | Enjoy 5G connectivity, Wi-Fi 6, and Bluetooth 5.3 support.... |
| `digital_ad::sent002...` | product_claim | unknown | comparative | (195, 206) | Learn more.... |
| `digital_ad::sent003...` | disclaimer | blog_disclaimers | numeric | (225, 306) | Network availability (including 5G) depends on carrier and coverage; speeds vary... |

**Summary:**
- Total extracted claims: 4
- Product claims: 3
- Disclaimer claims: 1
- Meta claims: 0
- **Note:** All sentences are exact substrings (offset-traceable)

---
## Example 2 — Faq
**Run ID:** `faq`  
**Product:** unknown | **Engine:** unknown  
**Extractor:** v2.0

### Generated Text Excerpt (Verbatim Model Output)

```
**FAQ for Nova X5 5G Smartphone (US)**

**Q1: What is the display size and resolution of the Nova X5?**  
A1: The Nova X5 features a 6.5 in display with a resolution of 2400×1080 pixels and a 120 Hz refresh rate for smoother on-screen motion.

**Q2: What is the battery capacity and charging specifications?**  
A2: The Nova X5 has a nominal battery capacity of 5000 mAh and supports 30 W USB-C wired

[... middle section omitted ...]

gies does the Nova X5 support?**  
A5: The Nova X5 supports 5G sub-6 GHz connectivity, Wi-Fi 6 networks, and Bluetooth 5.3 for wireless audio and accessories.

Disclaimers:  
Network availability (including 5G) depends on carrier and coverage; speeds vary.  
Actual battery life varies by usage, settings, and network conditions.  
Avoid liquid exposure; no water-resistance certification is claimed.
```

### Extracted Claims (Verbatim)

| Claim ID | Claim Kind | Block Kind | Triggers | Char Span | Sentence |
|----------|------------|------------|----------|-----------|----------|
| `faq::sent000...` | product_claim | unknown | numeric | (0, 38) | **FAQ for Nova X5 5G Smartphone (US)**... |
| `faq::sent001...` | disclaimer | faq_disclaimers | numeric | (960, 1041) | Network availability (including 5G) depends on carrier and coverage; speeds vary... |

**Summary:**
- Total extracted claims: 2
- Product claims: 1
- Disclaimer claims: 1
- Meta claims: 0
- **Note:** All sentences are exact substrings (offset-traceable)

---
## Example 3 — Blog Post
**Run ID:** `blog_post_promo`  
**Product:** unknown | **Engine:** unknown  
**Extractor:** v2.0

### Generated Text Excerpt (Verbatim Model Output)

```
# Introducing the Nova X5 5G Smartphone

The smartphone market is constantly evolving, and the latest addition to the lineup is the Nova X5 5G. This device is built for those who demand exceptional performance and cutting-edge technology. Let’s take a closer look at what makes the Nova X5 stand out.

## Stunning Display

One of the standout features of the Nova X5 is its impressive 6.5-inch displa

[... middle section omitted ...]

ts stunning display, robust performance, ample storage, and long-lasting battery life, it’s an excellent choice for anyone in the market for a new smartphone. 

**Disclaimers:** 
Network availability (including 5G) depends on carrier and coverage; speeds vary. Actual battery life varies by usage, settings, and network conditions. Avoid liquid exposure; no water-resistance certification is claimed.
```

### Extracted Claims (Verbatim)

| Claim ID | Claim Kind | Block Kind | Triggers | Char Span | Sentence |
|----------|------------|------------|----------|-----------|----------|
| `blog_post_promo::sen...` | product_claim | blog_title | numeric, claim_verb | (41, 143) | The smartphone market is constantly evolving, and the latest addition to the lin... |
| `blog_post_promo::sen...` | product_claim | blog_heading | numeric | (591, 704) | With a 120 Hz refresh rate, users can expect smoother on-screen motion, enhancin... |
| `blog_post_promo::sen...` | product_claim | blog_heading | numeric, claim_verb | (731, 867) | Under the hood, the Nova X5 is powered by an octa-core 2.4 GHz CPU, ensuring tha... |
| `blog_post_promo::sen...` | product_claim | blog_heading | numeric | (868, 977) | With 8 GB of RAM, multitasking becomes seamless, allowing you to switch between ... |
| `blog_post_promo::sen...` | product_claim | blog_heading | numeric, claim_verb | (1095, 1219) | The Nova X5 offers an impressive 256 GB of UFS 2.2 storage, providing plenty of ... |
| `blog_post_promo::sen...` | product_claim | blog_heading | numeric, claim_verb | (1946, 2050) | The Nova X5 supports 5G sub-6 GHz connectivity where available, ensuring you can... |

**Summary:**
- Total extracted claims: 9
- Product claims: 7
- Disclaimer claims: 2
- Meta claims: 0
- _(Showing 6 of 9 claims)_
- **Note:** All sentences are exact substrings (offset-traceable)

---
