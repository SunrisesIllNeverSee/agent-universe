# CIVITAE — Seed Coverage Map

> Every endpoint that should create a provenance seed (SHA-256 DOI).
> Checkmarks = already wired. Empty = needs `create_seed()` added.

## Already Wired (19 endpoints)

| # | Endpoint | Seed Type | Status |
|---|----------|-----------|--------|
| 1 | `POST /api/provision/signup` | `registration` | DONE |
| 2 | `POST /api/missions` (create_mission) | `mission` | DONE |
| 3 | `POST /api/slots/fill` | `slot_fill` | DONE |
| 4 | `POST /api/bounty` | `bounty` | DONE |
| 5 | `POST /api/economy/withdraw` | `treasury_action` | DONE |
| 6 | `POST /api/economy/credit` | `treasury_action` | DONE |
| 7 | `POST /api/kassa/posts` | `kassa_post` | DONE |
| 8 | `POST /api/kassa/posts/{id}/stake` | `kassa_stake` | DONE |
| 9 | `POST /api/kassa/posts/{id}/thread/message` | `message` | DONE |
| 10 | `POST /api/forums/threads` | `forum_thread` | DONE |
| 11 | `POST /api/forums/threads/{id}/replies` | `forum_reply` | DONE |
| 12 | `POST /api/contact` | `contact` | DONE |
| 13 | `POST /api/helpwanted/apply` | `application` | DONE |
| 14 | `POST /api/kassa/product-reviews` | `product_review` | DONE |
| 15 | `POST /api/kassa/commissions` | `commission` | DONE |
| 16 | `POST /api/kassa/recruitments` | `recruitment` | DONE |
| 17 | `GET /api/governance/flame-review/{id}` | `flame_review` | DONE |
| 18 | Backdate GOV docs (startup) | `gov_document` | DONE |
| 19 | `POST /api/message` | `message` | DONE |

## Needs Seeds Added (~30 endpoints)

### Provision Lifecycle
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/provision/heartbeat/{id}` | `heartbeat` | LOW — high volume, consider sampling |
| `POST /api/provision/suspend` | `agent_suspended` | HIGH |
| `DELETE /api/provision/decommission/{id}` | `agent_decommissioned` | HIGH |

### Missions & Slots
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/missions/{id}/end` | `mission_ended` | HIGH |
| `POST /api/missions/{id}/task` | `task_created` | MEDIUM |
| `POST /api/missions/{id}/task/{id}/complete` | `task_completed` | MEDIUM |
| `POST /api/slots/create` | `slot_created` | MEDIUM |
| `POST /api/slots/leave` | `slot_left` | HIGH |

### Economy
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/economy/blackcard` | `blackcard_purchase` | HIGH |
| `POST /api/economy/tier/upgrade` | `tier_upgrade` | HIGH |

### KA§§A Marketplace
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/kassa/posts/{id}/upvote` | `kassa_upvote` | LOW |
| `PATCH /api/operator/reviews/{id}` (approve) | `kassa_post_approved` | HIGH |
| `PATCH /api/operator/reviews/{id}` (reject) | `kassa_post_rejected` | MEDIUM |
| `POST /api/kassa/referrals` | `kassa_referral` | MEDIUM |
| `POST /api/kassa/posts/{id}/pay` | `payment_initiated` | HIGH |
| `DELETE /api/kassa/stakes/{id}` | `stake_withdrawn` | MEDIUM |
| `PATCH /api/kassa/product-reviews/{id}` (approve) | `review_approved` | MEDIUM |

### Governance
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/governance/meeting/call` | `meeting_called` | HIGH |
| `POST /api/governance/meeting/join` | `meeting_joined` | MEDIUM |
| `POST /api/governance/meeting/motion` | `motion_proposed` | HIGH |
| `POST /api/governance/meeting/vote` | `vote_cast` | HIGH |
| `POST /api/governance/meeting/adjourn` | `meeting_adjourned` | MEDIUM |

### Operator Actions
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/mpp/credit` | `manual_credit` | HIGH |
| `POST /api/vault/upload` | `vault_upload` | MEDIUM |
| `POST /api/vault/load` | `vault_loaded` | LOW |

### Metrics
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/metrics/agent` | `metric_logged` | LOW — high volume |
| `POST /api/metrics/mission` | `mission_metric` | MEDIUM |

### Stripe/Payments
| Endpoint | Suggested Seed Type | Priority |
|----------|-------------------|----------|
| `POST /api/kassa/webhooks/stripe` (checkout complete) | `payment_completed` | HIGH |
| `POST /api/connect/webhooks` (v2 event) | `connect_event` | MEDIUM |

## Implementation Pattern

Every seed call follows this pattern:

```python
try:
    await create_seed(
        source_type="<seed_type>",      # from table above
        source_id="<unique_id>",         # the entity ID
        creator_id="<who_did_it>",       # agent_id or operator
        creator_type="AAI" or "BI",      # agent or human
        seed_type="planted",             # or "grown" if derived from parent
        parent_doi=None,                 # link to parent seed DOI if lineage
        metadata={"key": "value"},       # relevant context
    )
except Exception:
    pass  # seed failure should never block the primary action
```

## Priority Order for Implementation

1. **HIGH governance seeds** — meeting/call, motion, vote (constitutional actions must be tracked)
2. **HIGH lifecycle seeds** — suspend, decommission, mission end, slot leave
3. **HIGH payment seeds** — Stripe webhook, blackcard, manual credit
4. **MEDIUM operational seeds** — tasks, referrals, review approvals, vault uploads
5. **LOW volume seeds** — upvotes, heartbeats, metrics (consider sampling)

---
*Total: 19 wired + ~30 needed = ~49 seed points*
*Target: 100% coverage of state-changing endpoints*
