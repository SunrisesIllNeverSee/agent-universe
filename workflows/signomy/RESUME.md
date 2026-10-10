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

## Completed this cycle
- Receipt integrity repaired (invalidate → retry → honest PASS, probe_exit=0).
- Shell falsifier corrections + real-browser QA (screenshots in reviews/p3-shell-qa/).
- X-Agent-Key credential transport; /api/pages census fix.

## Wiring Atlas v0.2 (completed 2026-10-10)
Archive: ~/Developer/_7_labs/signomy-control-surface/reports/wiring-atlas/
- v0.2 census: stable IDs, evidence classes, 314 decorated endpoints
  (199 api / 82 page_route / 3 ws / 30 mcp_tool) across 23 modules,
  JS+WS+nav+storage extraction, drift tracking (--check-drift),
  25 tests, falsifier + 4 reviewer rounds, PASS post-correction.
- Refresh (ORDER MATTERS — rebuild overwrites fingerprints):
  1. `python3 build_atlas.py --repo <repo> --archive <archive> --out <atlas> --check-drift`
  2. `python3 validate_runtime.py --base <local-url> --out <atlas>`
  3. `python3 build_atlas.py --repo <repo> --archive <archive> --out <atlas>`
- Serve: `python3 -m http.server 8931 --directory <atlas>`.

## Next eligible work (no new authorization needed)
1. Extend ctx derivation: /slots + /deploy query-param objects → Inspector.
2. P2 visual delta group specs → workflows/signomy/out/p2-delta-specs/
   (provisional labels; original masters as reference).
3. Shell interactive-flow falsifier: stake/post/vote inside canvas — verify
   backend authority still enforced (no merge).
4. Kill the local QA server (port 8912) when done previewing.

## Owner decisions outstanding (one packet)
workflows/signomy/evidence/OWNER-DECISION-PACKET.md — T0_ADVERSARIAL (now
backed by genuinely independent falsifier + real correction), T0_GATE,
P2_PROVISIONAL. P3_AUTHORIZE remains gated behind those in-graph.
