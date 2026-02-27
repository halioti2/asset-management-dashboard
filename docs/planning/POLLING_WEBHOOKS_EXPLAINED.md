# Polling vs Webhooks: Quick Reference Guide

## The Core Difference

**Polling:** Your app asks Google Sheets "Any updates?" at regular intervals
**Webhooks:** Google Sheets tells your app when something changes

---

## Visual Comparison

### Polling Flow
```
Your App:  "Any changes?"   →
Google:                     ← "Nope"
Your App:  "Any changes?"   →
Google:                     ← "Nope"
Your App:  "Any changes?"   →
Google:                     ← "Yes! Row 5 changed"
Your App:  [Updates UI]
```

**Like checking your mailbox every hour**

### Webhook Flow
```
User updates Google Sheet
        ↓
Google detects change
        ↓
Google sends notification to your app
        ↓
Your app receives notification → [Updates UI]
```

**Like signing up for email notifications**

---

## Quick Comparison Table

| Feature | Polling | Webhooks |
|---------|---------|----------|
| **Who initiates?** | Your app | Google |
| **Frequency** | Fixed interval (5s, 10s, etc.) | Event-driven (~3 min batches) |
| **API calls** | Continuous, even if no changes | Only when changes occur |
| **Latency** | 5-30 seconds typically | ~3 minutes (Google batches) |
| **Infrastructure** | Simple server | Needs public HTTPS endpoint |
| **Implementation** | Few lines of code | More complex setup |
| **When to use** | Single user, simple apps | Production, multiple users |

---

## Google Sheets API Quota Limits

**Critical Constraint:** 60 requests per minute per user

```
Polling Interval    Requests/Min    Status
1 second           60              ❌ AT LIMIT - FAILS
2 seconds          30              ✅ SAFE
5 seconds          12              ✅ SAFE
10 seconds         6               ✅ VERY SAFE
30 seconds         2               ✅ OPTIMAL
```

**For your single-user app:** 10-second polling is ideal (6 req/min)

---

## Polling Explained

### How It Works
```javascript
// Check every 10 seconds
setInterval(async () => {
  // Ask Google: "What's the latest data?"
  const newData = await sheets.get();

  // Compare with what we had before
  if (dataChanged(oldData, newData)) {
    // Tell the user
    notifyUser(newData);
    oldData = newData;
  }
}, 10000);
```

### When to Use
- ✅ Single user app
- ✅ Simple codebase
- ✅ No public hosting yet
- ✅ Low frequency of updates
- ✅ Quick prototypes

### When NOT to Use
- ❌ Multiple concurrent users (quota exceeded)
- ❌ Real-time updates critical
- ❌ Frequent polling needed (performance)
- ❌ Cost-sensitive (many API calls)

---

## Webhooks Explained

### How It Works
```javascript
// 1. Tell Google: "Notify me at this URL"
google.watch({
  fileId: SHEET_ID,
  webhookUrl: 'https://yourapp.com/webhook'
});

// 2. Listen for notifications
app.post('/webhook', async (req) => {
  // Google says: "Something changed!"
  // Fetch the data to see what changed
  const newData = await sheets.get();
  notifyUser(newData);
});
```

### Important: 3-Minute Batch Delay
Google doesn't send a webhook immediately. It batches all changes made in the last ~3 minutes and sends ONE notification.

```
2:00:00 - User 1 edits row 5
2:00:15 - User 2 edits row 7
2:01:30 - User 3 edits row 10

2:03:00 - Google sends ONE webhook notification
         (You find out about all 3 changes at once)
```

### When to Use
- ✅ Production app
- ✅ Multiple users
- ✅ Can tolerate 3-minute delays
- ✅ Want efficient API usage
- ✅ Have public HTTPS endpoint

### When NOT to Use
- ❌ Real-time updates needed (3 min lag)
- ❌ No public hosting yet
- ❌ Can't handle webhook complexity
- ❌ Simple MVP (too complex)

---

## Hybrid Approach (Best for Production)

Combine both for reliability:

```javascript
// Primary: Listen for webhooks (efficient)
app.post('/webhook', async () => {
  await syncSheetData();
});

// Fallback: Poll if webhook fails (reliable)
setInterval(async () => {
  if (tooMuchTimeSinceLastSync()) {
    await syncSheetData();
  }
}, 120000); // 2 minute fallback
```

**Result:**
- Gets updates within 3 minutes (webhook)
- If webhook fails, polling catches it in 2 minutes
- Efficient API usage
- Reliable

---

## For Your Single-User App (Right Now)

**Recommendation: Use Polling Every 10 Seconds**

```javascript
// Good for your current setup
const POLLING_INTERVAL = 10000; // 10 seconds

setInterval(async () => {
  try {
    const newData = await sheetsAPI.get({
      spreadsheetId: YOUR_SHEET_ID,
      range: 'Sheet1!A:E'
    });

    // Only notify if something changed
    if (hasChanges(cachedData, newData)) {
      broadcastToUI(newData);
      cachedData = newData;
    }
  } catch (error) {
    console.error('Sync failed:', error);
  }
}, POLLING_INTERVAL);
```

**Why 10 seconds?**
- Uses only 6 API calls per minute (10% of 60-limit)
- Leaves room for write operations
- Still responsive enough for single user
- Respects rate limits

---

## When to Switch to Webhooks

Move to webhooks when:
- [ ] Multiple concurrent users (3+)
- [ ] Hosting on public server (HTTPS available)
- [ ] Current polling causes quota issues
- [ ] Want more efficient API usage
- [ ] Have time to implement fallback polling

---

## Redis Role in This

Redis helps by:
- **Caching** data so you don't fetch from API every time
- **Batching** writes so one API call does multiple updates
- **Reducing** polling frequency (can poll less often if cache is good)

But:
- **Not required** for single user
- Start with in-memory caching first
- Add Redis only when scaling

---

## Decision Tree

```
Single user, MVP phase?
├─ YES → Use Polling (10s interval)
└─ NO → Go to next

Multiple users or production?
├─ YES → Use Hybrid (webhooks + polling)
└─ NO → Go to next

Performance problems with polling?
├─ YES → Consider webhooks
└─ NO → Keep polling
```

---

## TL;DR

- **Polling:** Ask Google repeatedly (simple, works everywhere, limited scalability)
- **Webhooks:** Google tells you when it changes (efficient, complex, scalable)
- **For your app now:** Polling every 10 seconds with in-memory caching
- **Later, when hosting:** Switch to hybrid approach
- **Don't:** Poll every 1 second (exceeds quota limit)
- **Do:** Use batching and caching to reduce API calls
