---
description: Fine-grained operational controls — compression, speed, reasoning depth, reasoning mode, response style, output format.
argument-hint: [control value|preset name]
---

# /command

Apply COMMAND bar control: "$ARGUMENTS". If empty, show all current settings.

## Controls

```
/command compression [0-10]     # signal compression level
/command speed [0-10]           # response speed vs depth tradeoff
/command length [0-10]          # response length calibration
/command reasoning deductive    # deductive | inductive | abductive | analogical | critical
/command depth deep             # shallow | moderate | deep
/command style direct           # direct | socratic | storytelling | visual | suggestive | empirical
/command format markdown        # conversational | document | markdown | code | chart
/command narrative 75           # narrative strength 0-100
/command                        # show all current settings
```

## Quick Presets

```
/command preset balanced        # moderate everything
/command preset sprint          # fast, concise, shallow, direct
/command preset deep-dive       # slow, thorough, deep, empirical
/command preset brief           # minimal, compressed, short
```

## Behavior

COMMAND bar settings apply to all subsequent responses. They combine with governance mode and posture. Changes are logged to the audit trail.
