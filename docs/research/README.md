# Research & Exploration

This folder contains exploratory work and analysis done before formalizing into structured docs.

## Naming Convention

**Format:** `YYYY_MM_DD_topic_description.md`

**Examples:**
- ✅ `2026_02_21_auth_comparison.md`
- ✅ `2026_02_22_database_performance_analysis.md`
- ✅ `2026_03_01_instagram_api_exploration.md`
- ❌ `auth-research.md` (no date)
- ❌ `02-21-2026_auth.md` (wrong date format)

**Why this format?**
- Files sort chronologically automatically
- Easy to find "what were we thinking in February?"
- Underscores for readability (no hyphens to avoid date confusion)
- Topic should be 2-4 words describing the investigation

## Required Structure

Every research document must have:

### 1. Title with Date (in the filename)
The filename already has the date, so your title can just be descriptive:
```markdown
# Authentication Architecture: Current vs. Recommended
```

### 2. TL;DR Section (at the top)
Scannable summary with key points:
```markdown
## TL;DR

**Problem:** [One sentence problem statement]

**Current:** [Current approach in one sentence]

**Recommendation:** [Proposed solution in one sentence]

**Decision:** [What you decided, or "To be determined"]
```

That's it! The rest is freeform. Write naturally, explore ideas, don't worry about structure.

## Philosophy

- **Freeform thinking** - Write naturally, don't worry about perfect structure
- **Date your files** - Use `YYYY_MM_DD_topic.md` format
- **Add TL;DR** - Quick summary at the top for future reference
- **Keep everything** - Research docs are valuable historical context

## Current Research

- `2026_02_21_auth_comparison.md` - OAuth token management strategies

## Purpose

Research docs serve as:
- Source material for formal RFCs, ADRs, and specs
- Historical context for "why did we choose this?"
- Reference for future similar problems
- Freeform exploration without pressure to be "correct"

---

**Note:** When research concludes, extract key decisions into formal docs (`/planning`, `/architecture`, etc.) but keep the research doc for reference.
