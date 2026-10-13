run1-fail-*.txt: INVALID. The scratchpad venv had been removed, so every run failed with "no such file" (not a test failure). Kept, not deleted.
run2: 40/40 passes, serial. run3: 4 parallel workers x 8 = 32/32 passes (loaded machine). No failure reproduced.
Root cause (per P4-EVIDENCE slice 12): external Google Fonts/GTM stalling Page.goto 'load'; fixed by --host-resolver-rules in the browser fixture (already on this base). Guard test added.
Venv rebuilt at scratchpad/p3venv (repo .venv + homebrew playwright 1.59 via .pth).
