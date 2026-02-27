# Research Document Template

**Status:** [Research Complete / In Progress]
**Date:** YYYY-MM-DD
**Purpose:** [What question are we answering?]

---

## TL;DR

- **Problem:** [What's currently broken or suboptimal]
- **Current:** [How it works now / current approach]
- **Recommendation:** [What you should do instead]
- **Decision:** [What was decided / what to implement]

---

## Sequence Diagram

[ASCII diagram showing interactions between systems/actors over time with swimlanes]

**Example:**
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Browser  │     │ Supabase │     │  Your    │     │  Google  │
│          │     │   Auth   │     │ Backend  │     │  OAuth   │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ 1. Sign in    │                │                │
     ├──────────────▶│                │                │
     │                │                │                │
     │ 2. Authenticated               │                │
     │◀───────────────┤                │                │
     │                │                │                │
     │ 3. Click "Connect YouTube"     │                │
     ├───────────────────────────────▶│                │
     │                │                │                │
     │                │                │ 4. Initiate   │
     │                │                │    OAuth      │
     │                │                ├───────────────▶│
     │                │                │                │
     │ 5. Redirect to Google          │                │
     │◀───────────────────────────────────────────────┤
     │                │                │                │
     │ 6. User grants permissions     │                │
     ├────────────────────────────────────────────────▶│
     │                │                │                │
     │                │                │ 7. Auth code  │
     │                │                │◀───────────────┤
     │                │                │                │
     │                │                │ 8. Exchange   │
     │                │                │    for tokens │
     │                │                ├───────────────▶│
     │                │                │                │
     │                │                │ 9. Tokens     │
     │                │                │◀───────────────┤
     │                │                │                │
     │                │  10. Save tokens to DB         │
     │                │◀───────────────┤                │
     │                │                │                │
     │ 11. "YouTube Connected!"       │                │
     │◀───────────────────────────────┤                │
     │                │                │                │
```

---

## Architecture Diagram

[ASCII diagram showing data flows, system architecture, or process flow]

**Example:**
```
┌─────────┐  1. Click "Connect"   ┌──────────────┐
│ Browser │ ─────────────────────▶│ Netlify Fn:  │
│         │                        │ /youtube/init│
└─────────┘                        └──────┬───────┘
                                          │ 2. Generate OAuth URL
                                          │    + state parameter
     ┌────────────────────────────────────┘
     │ 3. Redirect
     ▼
┌─────────────┐
│   Google    │  4. User grants permissions
│ OAuth Screen│
└──────┬──────┘
       │ 5. Redirect with code
       ▼
┌──────────────┐  6. Exchange code    ┌──────────┐
│ Netlify Fn:  │────────────────────▶ │  Google  │
│ /callback    │◀──────────────────── │ OAuth API│
└──────┬───────┘  7. Get tokens       └──────────┘
       │          (access + refresh)
       │ 8. Store in DB
       ▼
┌──────────────┐
│  Supabase DB │
│ oauth_tokens │
└──────┬───────┘
       │ 9. Redirect to /playlist-discovery?connected=true
       ▼
┌─────────┐
│ Browser │  "Connected ✓"
└─────────┘
```

---

## Data Flow Diagram

[ASCII diagram showing process flows, decision trees, state transitions, or system behavior]

**Example:**
```
API Call:
  ├─ Is access_token valid?
  │   ├─ Yes → Use it
  │   └─ No → Check if expired?
  │       ├─ Yes → Try refresh
  │       └─ No → Might be revoked, ask user to reconnect
  │
  └─ Refresh failed?
      ├─ Yes → Refresh token expired/revoked
      └─ Ask user to reconnect YouTube
```

Or for token lifecycle:
```
├── Access Token (1 hour)
│   └── Used for API calls only
│   └── Checked before each request
│
├── Refresh Token (6 months)
│   └── Stored securely in database
│   └── Only used when access token expires
│   └── Never sent to client
│
└── Token Storage
    └── Separate storage locations (security)
    └── Database for refresh tokens
    └── No localStorage for sensitive tokens
```

---

## Problem vs Solution Matrix

[Table comparing different approaches, trade-offs, or current vs proposed state]

**Example:**
```
| Approach | Real-World Usage | Status |
|----------|-----------------|--------|
| **Option 1: Require refresh_token upfront** | ❌ Not standard | Overly strict |
| **Option 2: Try & handle failures** | ✅ Industry standard | Recommended |
| **Option 3: Hybrid (Check expiry, then refresh if needed)** | ✅✅ Most common | Best practice |
```

Or as a comparison table:

```
| Scenario | Access Token Valid | Refresh Token Missing | Current Behavior | Recommended |
|----------|------|------|------|------|
| User views page | ✅ 58 min left | ✅ Present | Works | Works |
| User syncs immediately | ✅ 1 hour fresh | ❌ Invalid | ❌ Fails | ✅ Works with valid token |
| After 6 months | ❌ Expired | ❌ Expired | ❌ Fails | Ask reconnect |
```

---

## Real-World Examples

[Links to actual projects, code samples, or implementations with analysis of how they solve the problem]

**Example:**
```
**YouTube API Samples** - [github.com/youtube/api-samples](https://github.com/youtube/api-samples)
- **Pattern:** Server-side OAuth with database persistence
- **Key File:** `go/oauth2.go` - Shows token storage and refresh handling
- **Approach:** Stores refresh tokens, refreshes proactively before expiry
- **Lesson:** Google's own samples use proactive refresh strategy

**Supabase Auth (Official)** - [github.com/supabase/auth](https://github.com/supabase/auth)
- **Pattern:** JWT-based with OAuth provider support
- **Architecture:** Separate auth service, database-backed token storage
- **Insight:** Auth server is separate from app server (like your Netlify functions)
```

---

## Side-by-Side Comparison

[Code snippets, configuration examples, or architectural approaches shown in parallel]

**Example:**
```javascript
// ❌ OPTION 1: Strict (Requires refresh_token upfront)
if (!tokenRecord.refresh_token) {
  throw error('refresh_token_missing')  // Fails immediately
}

// ✅ OPTION 2: Lenient (Check expiry, refresh if needed)
const isExpired = new Date(tokenRecord.expires_at) <= new Date()

if (isExpired && !tokenRecord.refresh_token) {
  throw error('RECONNECT_NEEDED', 'Please reconnect YouTube')
}

if (isExpired && tokenRecord.refresh_token) {
  // Try to refresh
  try {
    const refreshed = await refreshToken()
    return refreshed.access_token
  } catch {
    throw error('REFRESH_FAILED', 'Please reconnect YouTube')
  }
}

// Access token still valid, use it even without refresh_token
return tokenRecord.access_token
```

---

## Sources

**Optional:** Only include if web search was used. When included, provide markdown-formatted links with executive summary of each source.

**Example (when websearch was used):**
```
- [YouTube API Samples - OAuth Implementation](https://github.com/youtube/api-samples/blob/master/go/oauth2.go)
  - Google's official reference implementation
  - Shows token storage and proactive refresh strategy
  - Demonstrates server-side OAuth with database persistence

- [Google OAuth Best Practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices)
  - Official guidance on token storage and refresh
  - Recommends separate storage for access vs refresh tokens
  - Emphasizes HTTPS-only and backend token management

- [Auth0 - Refresh Tokens Best Practices](https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/)
  - Industry perspective on token lifecycle
  - Explains refresh token rotation and security
  - Practical implementation patterns used in production
```

---

## Overview

[Optional: Detailed context, background, or problem explanation. Use this section if the TL;DR needs additional context to understand the full picture.]

---

## Notes for Claude Code

When creating research documents:
1. **TL;DR:** Start with problem/current/recommendation/decision format - scannable and actionable
2. **Sequence Diagram:** Show interactions between systems using swimlane format
3. **Architecture Diagram:** Use ASCII to visualize system flows (not just describe them)
4. **Data Flow Diagram:** Show decision trees, process flows, state transitions
5. **Problem vs Solution:** Always include trade-offs/comparisons - rarely is one approach universally "best"
6. **Real-World Examples:** Link to actual implementations - show don't just tell
7. **Side-by-Side Comparison:** Show code/config alternatives in parallel
8. **Sources:** ONLY include if websearch was used. When included, provide summary of each source explaining why it matters and what you learned from it
