# Planning Documents

This directory contains pre-work and project planning documents.

## What Goes Here

- **RFCs** (Request for Comments): Problem statements and proposed solutions
- **PRDs** (Product Requirements Documents): User stories and acceptance criteria
- **ADRs** (Architecture Decision Records): Technical decisions and rationale
- **Technical Specifications**: Implementation details and API contracts
- **Project Timelines**: Phase breakdowns and estimates

## Naming Convention

**Format:** `[TYPE]_brief_description.md`

**Document Types:**

| Type | Prefix | Purpose | Example |
|------|--------|---------|---------|
| RFC | `RFC_` | Problem statement + proposed solution | `RFC_youtube_oauth_tokens.md` |
| PRD | `PRD_` | User stories + acceptance criteria | `PRD_youtube_oauth_persistence.md` |
| ADR | `ADR_NNN_` | Architecture decisions (numbered) | `ADR_002_dual_auth_oauth.md` |
| Tech Spec | `tech_spec_` | Implementation details | `tech_spec_dual_auth.md` |
| Timeline | `timeline_` | Phase breakdowns | `timeline_auth_migration.md` |

**Examples:**
- ✅ `RFC_youtube_oauth_tokens.md`
- ✅ `PRD_grocery_list_sharing.md`
- ✅ `ADR_002_dual_auth_oauth.md` (note the number)
- ✅ `tech_spec_dual_auth.md`
- ✅ `timeline_auth_migration.md`
- ❌ `auth-rfc-2026.md` (no TYPE prefix, includes date in filename)
- ❌ `ADR_dual_auth.md` (missing sequence number for ADRs)

**Why this format?**
- TYPE prefix makes document purpose obvious at a glance
- Brief description is scannable in file listings
- No dates in filename (dates go in document header metadata)
- Use underscores for readability (not hyphens or camelCase)
- ADR numbers create chronological sequence of decisions

## Document Requirements

### All Planning Documents Should Include

**Required metadata (in document header):**
```markdown
**Status:** [Draft | Active | Accepted | Implemented | Deprecated]
**Date:** YYYY-MM-DD
**Owner:** [Solo Developer | Team Name]
```

**For RFCs:**
- Clear problem statement
- Root cause analysis
- Proposed solution
- Success criteria
- Open questions

**For PRDs:**
- User stories with acceptance criteria
- User flows (happy path + error paths)
- UI requirements
- Success metrics
- Out of scope section

**For ADRs:**
- Context and problem
- Decision made
- Alternatives considered
- Consequences (positive, negative, neutral)
- Implementation plan (if applicable)

### Linking to Research Documents

**When referencing research, always include:**

1. **Link to source document:**
   ```markdown
   See: [Auth Comparison Research](../research/2026_02_21_auth_comparison.md)
   ```

2. **Specific findings or data points:**
   ```markdown
   Research findings show 93% of surveyed Supabase+OAuth projects use dual auth.
   (Source: [Dual Auth Feasibility Research](../research/dual_auth_feasibility_research.md))
   ```

3. **Related documents section:**
   ```markdown
   **Related Documents:**
   - [RFC: YouTube OAuth Tokens](./RFC_youtube_oauth_tokens.md)
   - [Research: Auth Comparison](../research/2026_02_21_auth_comparison.md)
   ```

**Why this matters:**
- Traceability: Decisions can be traced back to data/research
- Credibility: Shows due diligence was done
- Future reference: Others can review the reasoning
- Learning: Documents the research process

### Research Documents Should Include Sources

When creating research documents in `/docs/research/`:

**Required sections:**
- **Methodology:** How was research conducted?
- **Sources:** External links, repos analyzed, docs referenced
- **Findings:** What was learned
- **Recommendations:** Actionable guidance

**Example source citations:**
```markdown
## Sources

**External Documentation:**
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)
- [Supabase Auth Guide](https://supabase.com/docs/guides/auth)

**Similar Projects Analyzed:**
- [spotify-playlist-manager](https://github.com/example/repo) - Supabase + Spotify OAuth
- [calendar-sync-tool](https://github.com/example/repo2) - Supabase + Google Calendar

**Community Resources:**
- [Supabase Discord: OAuth discussion thread](https://discord.com/channels/...)
- [Reddit r/webdev: Token storage patterns](https://reddit.com/r/webdev/...)
```

## Current Documents

- `RFC_youtube_oauth_tokens.md` - Problem statement for OAuth token management
- `PRD_youtube_oauth_persistence.md` - User requirements for persistent YouTube tokens
- `ADR_002_dual_auth_oauth.md` - Decision to implement dual authentication

## Next Steps

See `../PROJECT_DOCUMENTATION_GUIDE.md` for templates and detailed guidance.

