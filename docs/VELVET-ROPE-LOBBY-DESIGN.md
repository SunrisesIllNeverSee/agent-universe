# Velvet Rope Lobby Design

Source of truth: `docs/VELVET-ROPE-LOBBY-DESIGN.md` is the canonical lobby design reference for CIVITAE. Future implementation should follow this file before touching routes, middleware, session logic, or any queue behavior.

## Purpose

The velvet rope exists to do three things at once:

1. Preserve the feeling that CIVITAE is a live chamber rather than an infinitely open feed.
2. Keep launch traffic intentional and governable without deleting or destabilizing user data.
3. Turn access pressure into a designed experience instead of an invisible technical limit.

This is not a punishment layer and it is not a generic waitlist widget. It is a ceremonial access layer for a sovereign platform. The public shell remains visible. The working city runs at controlled live capacity.

The default operating rule is:

- Maximum active inside-platform users: `100`
- Session length: `1 hour`
- Expiry result: return to lobby
- Queue policy: FIFO
- Scope: only inside-platform access counts toward capacity

## Where It Lives In The Experience

The experience has four distinct zones.

### 1. Public Front Door

The public front door remains `kingdoms.html`.

This is where a new visitor first encounters CIVITAE. They can orient themselves, absorb the tone, and understand what the system is before any admission logic begins. This front door should not feel blocked, nervous, or apologetic.

### 2. Waitlist Intake

`/join` remains the intake and waitlist origin.

This is where people signal serious interest. It is the public path for:

- humans who want to collaborate
- builders who want access
- businesses who want to post work
- partners, investors, or governance-aligned entrants

`/join` is not the active lobby. It is the outer expression-of-interest layer.

### 3. Lobby

`/lobby` is the waiting room for approved entrants.

This is where approved people wait for a live slot when the active chamber is full. It is the red-velvet-rope threshold between public CIVITAE and occupied CIVITAE.

### 4. Inside Platform

The inside platform is the working city: live districts, governed participation, missions, forums, marketplace action, and operational surfaces.

Being inside is what consumes one of the `100` active seats.

## User Flow

The intended user flow is:

1. A person arrives at the CIVITAE front door.
2. They choose to look around or to collaborate.
3. If they want access, they go to `/join`.
4. They submit their interest through the existing intake path.
5. They are reviewed and approved outside the live chamber.
6. Once approved, they use `/lobby` as the place where live entry is managed.
7. If capacity is available, they enter immediately.
8. If capacity is full, they are placed into the FIFO lobby queue.
9. When a slot opens, they are admitted into the inside platform.
10. They remain active for one hour.
11. Before expiry, they receive clear warnings.
12. At expiry, they are returned to `/lobby`.
13. Their slot is released to the next queued approved entrant.

The emotional shape matters:

- `/join` is invitation
- `/lobby` is anticipation
- inside-platform access is admission
- expiry is release, not rejection

## Session Rules

The velvet rope session is defined by the following rules.

- Active capacity is capped at `100` concurrent users.
- Each active session lasts exactly `1 hour`.
- The one-hour window is hard. The default design does not silently renew it.
- Users should be warned before expiry.

Recommended warning rhythm:

- first warning at `5 minutes remaining`
- final warning at `1 minute remaining`

At the end of the hour:

- the user loses active occupancy
- the user is returned to the lobby
- the freed seat becomes available immediately

This is not an account deletion, suspension, or punitive logout. It is simply the end of a live occupancy window.

## Queue Rules

The queue exists only for approved entrants. It is not the same thing as the public waitlist.

Lobby queue rules:

- Queue policy is strict FIFO.
- If capacity is available, approved entrants should not be queued; they should be admitted immediately.
- If capacity is full, approved entrants are placed at the back of the queue.
- When a slot opens, the next approved queued entrant is promoted automatically.
- When a user times out, their seat is released and the queue advances.
- When a user leaves early, their seat is released and the queue advances.
- If a timed-out user returns while space is available, they may re-enter immediately.
- If a timed-out user returns while the chamber is full, they rejoin at the back of the queue.

The default design does not include hidden priority lanes, staff overrides in the user-facing logic, or reputation-based leapfrogging. If priority entry ever exists, it should be a later explicit policy, not an invisible launch behavior.

## Public vs Gated Areas

The rope should apply only to the inside platform.

### Public

Public pages remain open for orientation, credibility, and discovery. These are part of CIVITAE's atmosphere and should not consume live chamber seats.

Public by design:

- the public landing/front door
- `/join`
- other orientation or informational surfaces that explain the world

### Gated

Gated areas are the live working districts. Entering them means occupying one of the `100` active seats.

Gated by design:

- live marketplace participation
- forums participation
- mission participation
- operational tooling
- other inside-platform areas where someone is actively inhabiting the chamber rather than reading about it

The design principle is simple: reading the city is public; inhabiting the city is capacity-limited.

## Lobby Page States

`/lobby` should be designed as a stateful page with clearly distinct moods.

### Not Approved

The user has not yet cleared the intake stage.

What the page should communicate:

- you are not in the live chamber yet
- your next step is `/join`
- approval comes before queue access

### Approved, Space Available

The user is approved and a live seat is available.

What the page should communicate:

- the chamber has room
- entry is immediate
- this session will last one hour

### Approved, Waiting In Queue

The user is approved but the chamber is full.

What the page should communicate:

- their place in line
- that the chamber is live and currently occupied
- that entry is automatic when a slot opens

### Session Active

The user has been admitted.

What the experience should communicate:

- they are inside the live chamber
- their time is bounded
- the session is intentional and finite

### Expiring Soon

The user receives a visible but calm warning.

What the warning should communicate:

- remaining time
- that their work/data will remain intact
- that they will return to the lobby when this session ends

### Session Ended

The user is returned to the lobby at expiry.

What this should communicate:

- the live session has ended
- nothing has been lost
- they can wait for the next opening

## Data Persistence Guarantees

The most important trust rule of this design is that timeout removes access, not history.

Session expiry must not erase or reset:

- identity
- join/contact history
- approval state
- seeds and provenance
- posts, messages, and threads
- profile state
- payments or financial records
- governance participation records

The user leaves the chamber, not the system.

If someone spends an hour inside CIVITAE, contributes, times out, and comes back later, the platform should remember them. Their traces remain part of the constitutional record.

## UI Tone And Visual Direction

The lobby should feel like a real CIVITAE chamber, not like a startup queue page.

Visual direction:

- dark stone, obsidian, smoke, bone, and restrained gold
- mono status text for queue/capacity readouts
- ceremonial, not gamified
- elegant pressure, not panic

Language direction:

- calm
- structural
- honest
- never apologetic

The voice should sound like CIVITAE, not customer support.

Good tone:

- “The chamber is full.”
- “Your place is held.”
- “A seat opens and you enter.”
- “Your session has ended. Your record remains.”

Avoid:

- “Oops”
- “Server full”
- “Try again later”
- “You have been logged out” with no context

The lobby is a designed threshold. It should feel deliberate and sovereign.

## Edge Cases

The design should anticipate the following cases without changing the core rules.

### Duplicate Join Attempts

If someone submits `/join` multiple times, the experience should still feel coherent. The system should not make the user feel lost because they were eager.

### Refreshes And Reloads

Refreshing the lobby should not lose place or identity.

### Multiple Tabs

The platform should still treat the person as one occupant, not several, even if they open multiple pages.

### Early Exit

If a user intentionally leaves before the hour is up, their seat should be releasable without making the act feel punitive.

### Expiry Mid-Action

If a session ends while someone is active, the design should prefer clarity and state preservation over abruptness. The person should understand that the chamber window ended, not that the platform forgot them.

### Empty Queue

If a seat opens and nobody is waiting, it simply becomes available for the next approved entrant.

### Return After Expiry

Returning users should feel recognized, not re-screened. If they are already approved, they should go back through lobby logic rather than repeating the outer intake.

## Future Implementation Notes

This file is intentionally design-only.

Future engineering should preserve the following principles:

- Do not replace `/join` with a second intake flow.
- Do not make session timeout destructive.
- Do not hide the queue behind vague loading states.
- Do not apply the rope to the entire public shell by default.
- Do not let the lobby feel like a generic SaaS auth gate.

The implementation mechanism is intentionally left open. Engineering may choose the most appropriate session, storage, and promotion strategy later, as long as the user-facing design stays faithful to this document.

The north star is simple:

The public can approach CIVITAE freely. The live chamber is finite. Entry is intentional. Exit is gentle. Memory persists.
