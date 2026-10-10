# RESUME — exact next commands

Repo: ~/Developer/_5_Signomy/1_agent-universe
Branch: feat/signomy-p3-shell (isolated; do NOT merge)

## Verify state
```bash
cd ~/Developer/_5_Signomy/1_agent-universe
git checkout feat/signomy-p3-shell
.venv/bin/python -m pytest tests/ -x -q                    # expect 527/527
python3 -m roadmap_engine --project workflows/signomy verify   # receipts
python3 -m roadmap_engine --project workflows/signomy drift    # expect clean
python3 -m roadmap_engine --project workflows/signomy status
```

## Next eligible work (no new authorization needed)
1. Shell independent-falsifier pass: probe hosted-route integrity, context
   persistence, no-write enforcement, deep-link behavior; write
   reviews/P3-Shell-Falsifier-* artifacts; apply bounded corrections.
2. Expand shell context: kassa post deep-link → post_id Inspector field is
   live; mission/slot refs derive from URL — extend coverage to /slots,
   /deploy query params; keep read-only.
3. Visual delta group specs (P2): draft per-group delta specs under
   workflows/signomy/out/p2-delta-specs/ using original design masters as
   reference; label provisional.
4. Push branch: git push -u origin feat/signomy-p3-shell (safe; no merge).

## Owner decisions outstanding (one packet)
workflows/signomy/evidence/OWNER-DECISION-PACKET.md — T0_ADVERSARIAL (now
backed by genuinely independent falsifier + real correction), T0_GATE,
P2_PROVISIONAL. P3_AUTHORIZE remains gated behind those in-graph.
