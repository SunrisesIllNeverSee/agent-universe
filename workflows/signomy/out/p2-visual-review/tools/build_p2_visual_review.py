#!/usr/bin/env python3
"""Offline builder for the P2 visual review pages (PROPOSAL assets only).

Reads the DG1-DG6 specs + p2-delta-specs.json, embeds downscaled previews of the
original masters (read-only), draws annotated SVG proposal mocks, and writes
static HTML pages + manifest.json. No network, no external assets.
Requires Pillow (preview downscale only).  Run from anywhere.
"""
import base64, hashlib, html, io, json, re
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
SPECS = OUT.parent / "p2-delta-specs"
CW = Path("/Users/dericmchenry/Developer/_7_labs/signomy-control-surface")
SRC = CW / "source/SIGNOMY-CIVITAE-design-handoff"
D2 = SRC / "02-diagrams"
MP = SRC / "01-magicpath"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# ---------------------------------------------------------------- spec parsing
def parse_spec(md):
    items, cur = [], None
    for line in md.read_text().splitlines():
        m = re.match(r"### (DG\d-[UX]\d+) - (.*)", line)
        if m:
            cur = {"id": m[1], "title": m[2], "status": "", "cites": [], "changes": []}
            items.append(cur); continue
        if line.startswith("## ") and not line.startswith("### "): cur = None
        if not cur: continue
        m = re.match(r"\*\*Status:\*\* (.*)", line)
        if m: cur["status"] = m[1].strip()
        m = re.match(r"- (1[A-G]) `([^`]+)` - (§.*)", line)
        if m: cur["cites"].append({"contract": m[1], "file": m[2], "section": m[3].strip()})
        m = re.match(r"- \[(\w+)\] (.*)", line)
        if m: cur["changes"].append((m[1], m[2]))
    return items

spec = json.loads((SPECS / "p2-delta-specs.json").read_text())
GROUPS = {g["group_id"]: g for g in spec["groups"]}
ITEMS = {gid: parse_spec(SPECS / g["spec_file"]) for gid, g in GROUPS.items()}

# ---------------------------------------------------------------- image embed
def data_uri(path, width, quant=True):
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    if quant: im = im.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), im.size

# ---------------------------------------------------------------- svg helpers
E = html.escape
class Svg:
    def __init__(self, w, h): self.w, self.h, self.p = w, h, []
    def add(self, s): self.p.append(s)
    def box(self, x, y, w, h, label, kind="orig", sub=None, fs=12):
        cls = {"orig": "o", "prop": "p", "nom": "n", "ro": "r", "unres": "u", "zone": "z"}[kind]
        self.add(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>')
        lines = label.split("\n")
        ty = y + h / 2 - (len(lines) - 1) * (fs + 1) / 2 + (4 if not sub else -2)
        for i, l in enumerate(lines):
            self.add(f'<text x="{x + w/2}" y="{ty + i*(fs+2)}" font-size="{fs}" text-anchor="middle">{E(l)}</text>')
        if sub:
            self.add(f'<text x="{x + w/2}" y="{y + h - 7}" font-size="9" text-anchor="middle" class="sub">{E(sub)}</text>')
    def zone(self, x, y, w, h, title, kind="p"):
        self.add(f'<rect class="zone {kind}z" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')
        self.add(f'<text x="{x+10}" y="{y+16}" font-size="11" class="zt">{E(title)}</text>')
    def arrow(self, pts, label=None, kind="p", lx=None, ly=None):
        d = " ".join(f"{x},{y}" for x, y in pts)
        self.add(f'<polyline class="a{kind}" points="{d}" fill="none" marker-end="url(#ah{kind})"/>')
        if label:
            mx = lx if lx is not None else (pts[0][0] + pts[-1][0]) / 2
            my = ly if ly is not None else (pts[0][1] + pts[-1][1]) / 2 - 4
            self.add(f'<text x="{mx}" y="{my}" font-size="9.5" text-anchor="middle" class="al">{E(label)}</text>')
    def text(self, x, y, s, fs=11, cls="", anchor="start"):
        self.add(f'<text x="{x}" y="{y}" font-size="{fs}" class="{cls}" text-anchor="{anchor}">{E(s)}</text>')
    def chain(self, x, y, w, h, gap, labels, kind="prop", fs=11, edge=None):
        xs = []
        for i, l in enumerate(labels):
            bx = x + i * (w + gap); xs.append(bx)
            k = kind[i] if isinstance(kind, list) else kind
            self.box(bx, y, w, h, l, k, fs=fs)
            if i: self.arrow([(bx - gap, y + h / 2), (bx, y + h / 2)], None, "p")
        return xs
    def render(self, title):
        defs = ('<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                '<rect width="8" height="8" fill="#2a1114"/><line x1="0" y1="0" x2="0" y2="8" stroke="#e5484d" stroke-width="2" opacity=".55"/></pattern>'
                + "".join(f'<marker id="ah{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                          for k, c in (("p", "#f5a623"), ("o", "#9a9a9a"), ("r", "#7aa2f7"), ("u", "#e5484d")))
                + '</defs>')
        return (f'<svg class="mock" viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{E(title)}" xmlns="http://www.w3.org/2000/svg">'
                + defs + "".join(self.p) + "</svg>")

def legend_svg():
    s = Svg(900, 34)
    items = [("orig", "ORIGINAL (unchanged)"), ("prop", "PROPOSAL (provisional)"), ("ro", "PROPOSAL read-only projection"), ("nom", "NO ORIGINAL MASTER - not approved"), ("unres", "UNRESOLVED / OWNER DECISION")]
    x = 6
    for k, l in items:
        s.box(x, 6, 20, 20, "", k); s.text(x + 26, 21, l, 11, "lg"); x += 26 + len(l) * 6.3 + 22
    return s.render("legend")

# ---------------------------------------------------------------- per-group mocks
def mock_dg1():
    s = Svg(1400, 1290)
    s.text(20, 22, "PROPOSAL OVERLAY on the original FigJam map - the original layout stays the master; this is NOT a replacement diagram.", 12, "hd")
    zones = ["PLATFORM /\nCONNECTION", "IDENTITY /\nUSER SPACE", "COMMAND /\nOPERATIONS", "MISSION /\nWORK", "SIG /\nPERFORMANCE", "KA§§A /\nMARKET", "ECONOMY", "COMMUNICATION", "CIVIC /\nGOVERNANCE", "WORLD /\nPROVENANCE"]
    s.text(20, 48, "Original zones (unchanged; from system-interaction-map.png)", 11, "sub2")
    for i, z in enumerate(zones): s.box(20 + i * 137, 56, 128, 44, z, "orig", fs=10)
    # A: agreement stack
    s.zone(20, 125, 1360, 330, "A. AGREEMENT STACK  (DG1-U1, U2, U3)  PROPOSAL")
    s.box(40, 160, 130, 44, "KA§§A Market Post\n(original node)", "orig", fs=10)
    s.box(230, 160, 120, 44, "entry intent", "prop")
    s.box(410, 150, 190, 64, "WorkEntryAgreement", "prop", sub="one model, one node", fs=13)
    s.box(680, 160, 160, 44, "Mission / Slot binding", "prop")
    s.arrow([(170, 182), (230, 182)], "enters", "p"); s.arrow([(350, 182), (410, 182)], None, "p"); s.arrow([(600, 182), (680, 182)], "binds", "p")
    s.arrow([(105, 204), (105, 236), (760, 236), (760, 206)], "NO direct post -> slot edge (1A S2 rule 2 / 1A S5.2 F13)", "u", 430, 230)
    for i, (c, t) in enumerate([("Open", "auto-accept after preconditions"), ("Standard", "pending + resolver"), ("Constitutional", "pending + required governance gate")]):
        s.box(870, 150 + i * 40, 90, 32, c, "prop", fs=11); s.text(968, 171 + i * 40, t, 10, "sub2")
    s.box(1200, 150, 160, 44, "CIVIC / GOVERNANCE\n(original zone)", "orig", fs=10)
    s.arrow([(1280, 194), (1280, 270), (520, 270), (520, 214)], "gate: Constitutional mode only", "p", 900, 264)
    s.text(40, 262, "Edge label: 'commitment order, not record-creation order' (slots may pre-exist).", 10, "sub2")
    classes = ["PlatformParticipation", "WorkEntry", "MissionWork", "Formation", "Contribution", "EntityRelation", "EntityNode", "EnterpriseDelegatedDomain", "ContributionBackedAccess", "ReciprocalEconomics"]
    s.text(40, 296, "Ten Agreement classes in registry order (1A S5.11) - registry is 'at minimum and extensible':", 11, "hd2")
    for i, c in enumerate(classes):
        s.box(40 + (i % 5) * 268, 308 + (i // 5) * 62, 256, 48, c, "prop", sub=f"class {i+1}", fs=11)
    s.text(40, 448, "Cluster caption: typed governed relationship object; 'active' is the only state that authorizes governed execution. Agreement emits Seeds/receipts and gates Mission/Slots/Formation.", 10, "sub2")
    # B: entity graph
    s.zone(20, 475, 1360, 250, "B. ENTITY GRAPH  (DG1-U4, U5)  PROPOSAL - six distinct nodes; chain must not be compressed")
    labs = ["ENTITY\n(identity)", "ENTITY NODE", "ROOT SEED", "SECONDARY\nSEEDS", "RELATIONS\n+ FLOWS", "ECOSYSTEM", "GROWTH"]
    xs = s.chain(40, 505, 150, 48, 28, labs, ["prop", "nom", "prop", "prop", "prop", "prop", "prop"], 10)
    s.text(xs[1], 570, "Entity Node: NO ORIGINAL MASTER", 9, "nm")
    s.box(xs[2] - 6, 590, 170, 50, "Node Recognition Office", "nom", fs=11)
    s.arrow([(xs[2] + 79, 590), (xs[2] + 79, 553)], "recognizes", "p", xs[2] + 130, 575)
    s.box(40, 600, 220, 50, "COMMUNICATION / Town Hall\n(original node)", "orig", fs=10)
    s.arrow([(260, 625), (xs[2] - 6, 615)], "petition intake / deliberation / notice (workflow only, not authority)", "p", 410, 600)
    s.box(40, 668, 220, 40, "Candidate projection (derived)", "ro", sub="no authority", fs=10)
    s.arrow([(260, 688), (xs[2] + 20, 640)], "feeds petition", "r", 440, 690)
    s.text(740, 640, "Existing 'Districts / Entities' = World projection label, NOT Entity Node.", 10, "sub2")
    s.text(740, 658, "Existing runtime 'Seeds' stay 'runtime provenance Seed' - not Root/Secondary until Node-qualified.", 10, "sub2")
    s.text(740, 676, "No label may read Entity = Entity Node = Ecosystem.", 10, "sub2")
    # C: enterprise
    s.zone(20, 745, 1360, 200, "C. ENTERPRISE CHAIN (DG1-U6) PROPOSAL - NO ORIGINAL MASTER for Enterprise Entity Node - not approved")
    el = ["ENTERPRISE\nENTITY", "COMMERCIAL\nAGREEMENT", "ENTERPRISE\nENTITY NODE", "ROOT SEED", "DELEGATED\nGOV. DOMAIN", "SUBORDINATE\nNODES", "SECONDARY SEEDS\n+RELS+FLOWS", "CONTROLLED ECO\nPROJECTIONS", "ENTERPRISE ECON /\nLICENSING / OPS"]
    xk = s.chain(36, 775, 128, 52, 18, el, ["prop", "prop", "nom", "prop", "prop", "prop", "prop", "ro", "prop"], 9)
    s.box(36, 870, 260, 52, "CIVIC / GOVERNANCE (Constitution/Vault)\n(original zone)", "orig", fs=9)
    s.arrow([(296, 896), (xk[4] + 64, 896), (xk[4] + 64, 827)], "parent constitutional override / audit", "p", 560, 888)
    s.text(760, 884, "Caption: buy-in != network-wide constitutional authority; commercial access != constitutional control.", 10, "sub2")
    s.text(760, 902, "Legend: private authoritative | private enterprise projection | public verification projection.", 10, "sub2")
    # D: derived projections + governance boundary
    s.zone(20, 965, 700, 300, "D. DERIVED READ-ONLY PROJECTIONS (DG1-U7, X1) PROPOSAL", "r")
    s.box(40, 1000, 200, 56, "AUTHORITATIVE STATE\n(Agreements, receipts, Seeds)", "orig", fs=10)
    s.box(300, 995, 190, 56, "Refinery", "nom", sub="boundary level only - UNRESOLVED DG1-X1", fs=13)
    s.box(300, 1075, 190, 56, "Switchboard", "nom", sub="boundary level only - UNRESOLVED DG1-X1", fs=13)
    s.box(520, 995, 180, 56, "World / Kingdom\nProjection (original)", "orig", fs=10)
    s.box(520, 1075, 180, 56, "SIG / PERFORMANCE\nmeasurement (original)", "orig", fs=10)
    s.arrow([(240, 1020), (300, 1023)], None, "r"); s.arrow([(240, 1040), (270, 1103), (300, 1103)], None, "r")
    s.text(40, 1160, "Arrows only INTO projections. No return arrow. No input/output edges invented.", 10, "sub2")
    s.text(40, 1178, "Switchboard: constrained routing/suggestion; ranking != eligibility.", 10, "sub2")
    s.text(40, 1196, "Refinery: interpretive projection; class selection is not a merit signal.", 10, "sub2")
    s.text(40, 1214, "No external semantics are asserted. Phase 6B/6C is not frozen.", 10, "nm")
    s.zone(740, 965, 640, 300, "E. FORMAL GOVERNANCE BOUNDARY vs TOWN HALL (DG1-U8)  PROPOSAL")
    s.add('<rect x="760" y="990" width="360" height="190" rx="8" fill="none" stroke="#f5a623" stroke-width="2.5"/>')
    s.text(770, 1008, "formal governance (standing from contracts, never purchased)", 10, "sub2")
    for i, l in enumerate(["Governance", "Senate", "Meetings", "Motions", "Votes"]):
        s.box(776 + (i % 3) * 112, 1022 + (i // 3) * 56, 104, 44, l, "orig", fs=11)
    s.box(1150, 1000, 210, 56, "Town Hall", "orig", sub="community surface, outside the line", fs=12)
    s.box(1150, 1076, 210, 56, "Forums", "orig", sub="COMMUNICATION, outside the line", fs=12)
    s.box(776, 1200, 330, 44, "Admin key edge: 'operational, not standing'", "unres", fs=10)
    s.text(1150, 1160, "Town Hall != formal Governance (1G S5.E).", 10, "sub2")
    return s.render("DG1 proposal overlay")

def mock_dg2():
    s = Svg(1400, 760)
    s.text(20, 22, "PROPOSAL annotation set over the original Operational Spine (original densely connected composition is preserved; not shown here).", 12, "hd")
    s.text(20, 46, "Spine of commitments (commitment order, not record-creation order):", 11, "sub2")
    labs = ["opportunity", "entry intent", "Agreement", "mission / work", "slot / formation", "governed\nexecution"]
    xs = s.chain(30, 60, 190, 56, 40, labs, ["orig", "prop", "prop", "orig", "orig", "orig"], 12)
    s.text(30, 136, "orig-styled nodes exist in original (KA§§A Opportunity, Mission, Slots/Roles, Formation); entry intent and Agreement are PROPOSAL additions.", 10, "sub2")
    s.zone(30, 160, 700, 150, "Open / Standard / Constitutional resolution at entry (DG2-U2) PROPOSAL")
    for i, (c, t) in enumerate([("Open", "auto-accept after preconditions"), ("Standard", "pending + resolver"), ("Constitutional", "pending + governance gate")]):
        s.box(50 + i * 220, 190, 200, 54, c, "prop", sub=t, fs=13)
    s.arrow([(xs[2] + 95, 116), (xs[2] + 95, 160)], None, "p")
    s.text(50, 276, "Resolver/timeout/notification detail intentionally NOT drawn (OWNER DECISION DG2-X1 / Q4).", 10, "nm")
    s.text(50, 296, "Gate only on consequential transitions (O-J-4 per-transition rule), not on all.", 10, "sub2")
    s.zone(760, 160, 610, 150, "Delivery / acceptance / settlement (DG2-U4) PROPOSAL")
    s.chain(776, 200, 170, 50, 26, ["delivery\n(evidence class)", "acceptance", "settlement"], "prop", 11)
    s.text(776, 278, "Evidence class chip: private / counterparty / public (1C S9.2).", 10, "sub2")
    s.zone(30, 330, 700, 150, "Provenance (DG2-U5) PROPOSAL")
    s.box(50, 365, 190, 50, "Seeds at consequential\ntransitions", "prop", fs=11)
    s.box(260, 365, 200, 50, "Failure writes NO\nsuccess Seed", "unres", fs=11)
    s.box(480, 365, 230, 50, "Audit chain (original)", "orig", fs=11)
    s.arrow([(240, 390), (260, 390)], None, "p"); s.arrow([(460, 390), (480, 390)], None, "o")
    s.zone(760, 330, 610, 150, "Projections stay read-only (DG2-U6) PROPOSAL", "r")
    for i, l in enumerate(["World", "Tier / Leaderboard", "Refinery", "Switchboard"]):
        s.box(776 + i * 148, 366, 138, 48, l, ["orig", "orig", "nom", "nom"][i], fs=11)
    s.text(776, 450, "Inbound arrows only. Refinery/Switchboard: NO ORIGINAL MASTER - boundary level only.", 10, "nm")
    s.zone(30, 500, 1340, 220, "Runtime context ribbon (DG2-U7, DG2-X1) - a SEPARATE LENS, not the spine  PROPOSAL")
    rl = ["opportunity /\npost", "agreement /\nentry", "slot", "mission", "formation", "motion", "settlement", "provenance /\nSeed"]
    for i, l in enumerate(rl):
        s.box(50 + i * 165, 540, 150, 50, l, "unres" if l in ("motion", "settlement") else "prop", fs=10)
        if i: s.arrow([(50 + i * 165 - 15, 565), (50 + i * 165, 565)], None, "p")
    s.text(50, 620, "Items without a live key render as 'not carried', never invented. 'motion' and 'settlement' key ids are OWNER DECISION (DG2-X1).", 10, "nm")
    s.text(50, 640, "Caption: 'Agreement != WorkEntry UI carry' - the ribbon is a navigation lens (1A S2 rule 4); the Agreement lives in authoritative state.", 10, "sub2")
    s.text(50, 700, "The original spine is edge-dense; this overlay is explanatory and is never a substitute for it.", 10, "sub2")
    return s.render("DG2 proposal annotations")

def mock_dg3():
    s = Svg(1400, 900)
    s.text(20, 22, "PROPOSAL annotations over the original Mission Lifecycle state flow (original states retained; new states drawn dashed).", 12, "hd")
    s.zone(20, 40, 1360, 130, "Entry (DG3-U1) PROPOSAL - hybrid WorkEntry states BEFORE MissionDraft / FormationOpen")
    xs = s.chain(36, 76, 134, 46, 16, ["Opportunity\n(orig)", "intent", "pending", "accepted", "active", "MissionDraft\n(orig)", "FormationOpen\n(orig)", "Matching\n(orig)"], ["orig", "prop", "prop", "prop", "prop", "orig", "orig", "orig"], 10)
    s.text(36, 146, "Open mode: intent -> accepted immediately after preconditions. Standard: pending + resolver. Constitutional: pending + required governance gate (1A S5.2 F6).", 10, "sub2")
    s.zone(20, 190, 1360, 130, "Exception / terminal entry states (DG3-U6) PROPOSAL - Q6: main canvas or collapsible overlay?")
    s.chain(36, 226, 160, 46, 30, ["rejected", "expired", "withdrawn", "disputed", "terminated"], "prop", 11)
    s.text(36, 300, "Terminal exception nodes carry the 1A S4.1 state names; placement (main canvas vs overlay) is OWNER DECISION Q6.", 10, "sub2")
    s.zone(20, 340, 1360, 170, "Gates drawn per-transition (DG3-U2, U3) PROPOSAL")
    s.box(36, 376, 170, 46, "FormationReady\n(orig)", "orig", fs=10); s.box(260, 376, 170, 46, "FormationAgreement\ngate", "prop", fs=10)
    s.box(490, 376, 170, 46, "DeployReady\n(orig)", "orig", fs=10); s.box(720, 376, 170, 46, "GovernanceCheck\n(orig)", "orig", fs=10)
    s.box(950, 376, 200, 46, "MissionWork Agreement\nactive?", "prop", fs=10)
    for a, b in [(206, 260), (430, 490), (660, 720), (890, 950)]: s.arrow([(a, 399), (b, 399)], None, "p")
    s.text(36, 450, "Governance gate appears only on transitions where O-J-4 categories fire (consequential), not drawn as a per-phase blanket.", 10, "sub2")
    s.text(36, 470, "Agreement state 'active' is the only state authorizing governed execution (1A S1.1 / S4.1).", 10, "sub2")
    s.zone(20, 530, 1360, 190, "Delivery, settlement, provenance (DG3-U4, U5) PROPOSAL")
    s.chain(36, 566, 150, 46, 24, ["InProgress\n(orig)", "Review\n(orig)", "Complete\n(orig)", "Settlement\n(orig)", "ReputationUpdate\n(orig)", "Seeded\n(orig)", "Audited\n(orig)", "WorldProjection\n(orig)"], "orig", 10)
    s.box(210, 640, 190, 40, "DeliveryEvidenceClass chip", "prop", fs=10); s.arrow([(305, 640), (261, 612)], None, "p")
    s.box(440, 640, 230, 40, "authoritative receipt + Seed", "prop", fs=10); s.arrow([(555, 640), (555, 612)], None, "p")
    s.box(710, 640, 250, 40, "failure writes NO success Seed", "unres", fs=10)
    s.zone(20, 740, 1360, 140, "Escrow / funding precondition on activation (DG3-X1) OWNER DECISION Q5")
    s.box(40, 776, 330, 52, "escrow_funded precondition\n(mechanism PENDING - 1G S5.H GAP)", "unres", fs=10)
    s.text(400, 800, "Depict, or omit until a mechanism exists? Not drawn as an existing capability.", 11, "nm")
    return s.render("DG3 proposal annotations")

def mock_dg4():
    s = Svg(1400, 880)
    s.text(20, 22, "PROPOSAL vocabulary updates inside the ORIGINAL grammar (nine-step flow order unchanged; additive annotations only).", 12, "hd")
    steps = ["User invokes\naction", "Resolve active\nprincipal", "Governance /\npermission\npreflight", "Show consequence\nstate+economy+\nevidence", "Confirm", "Commit state\ntransition", "Emit live\nevent", "Write Seed /\nAudit evidence", "Refresh all\nprojections"]
    xs = s.chain(20, 50, 130, 66, 14, steps, "orig", 10)
    for i, n in enumerate(range(1, 10)): s.text(xs[i] + 4, 46, str(n), 10, "sub2")
    s.box(xs[1], 140, 130, 100, "P1 human\nP2 agent\nP3 operator-FOR\nP4 admin (ops)\nP5 Entity anchor\nP6-P8 affil/ent/deleg", "prop", fs=9)
    s.arrow([(xs[1] + 65, 140), (xs[1] + 65, 116)], None, "p")
    s.text(xs[1] - 4, 256, "credential != principal class", 9, "nm")
    s.box(xs[2] - 20, 140, 170, 100, "in-path preconditions always;\ndiscretionary gate only\nfor the 8 O-J-4 categories", "prop", fs=9)
    s.arrow([(xs[2] + 65, 140), (xs[2] + 65, 116)], None, "p")
    s.box(xs[3] - 10, 140, 180, 100, "Value Strip: treasury movement\n| escrow (mechanism pending)\n| stake (intent, no funds)\n+ Evidence class chip", "prop", fs=9)
    s.arrow([(xs[3] + 80, 140), (xs[3] + 80, 116)], None, "p")
    s.text(20, 290, "Context Breadcrumb + Object Identity Block (DG4-U2) PROPOSAL", 12, "hd2")
    for i, (l, k) in enumerate([("Entity (identity)", "orig"), ("Campaign", "orig"), ("Agreement (optional)", "prop"), ("Mission", "orig"), ("Object", "orig")]):
        s.box(20 + i * 190, 304, 170, 40, l, k, fs=11)
        if i: s.arrow([(20 + i * 190 - 20, 324), (20 + i * 190, 324)], None, "p")
    s.text(20, 366, "'Entity' here means Entity (identity), not Entity Node. Agreement segment appears only when the object is Agreement-governed.", 10, "sub2")
    s.box(20, 380, 560, 60, "Object Identity Block:  ID | name | type | state   + PROPOSED: Agreement id/class/state, principal class", "prop", fs=10)
    s.text(20, 480, "Canvas adapters (DG4-U5) - read-only marks", 12, "hd2")
    ad = [("DEPLOY\nadapter", "orig"), ("MARKET\nadapter", "orig"), ("MISSION\nadapter", "orig"), ("CIVIC\nadapter", "orig"), ("WORLD adapter\n(tag: read-only)", "ro"), ("Refinery adapter\nread-only stub", "nom"), ("Switchboard adapter\nread-only stub", "nom")]
    for i, (l, k) in enumerate(ad): s.box(20 + i * 195, 496, 180, 60, l, k, fs=10)
    s.text(20, 576, "Read-only adapters show NO commit / write control and no destructive Action Stack items. Refinery/Switchboard: NO ORIGINAL MASTER.", 10, "nm")
    s.text(20, 616, "Action Stack (DG4-U6)", 12, "hd2")
    s.box(20, 630, 250, 40, "primary / secondary / destructive", "orig", fs=10)
    s.box(290, 630, 560, 40, "caption: each action inherits its 1G verb row; consent class shown in preflight", "prop", fs=10)
    s.text(20, 700, "Persistent application grammar items 3 (Context Tabs), 7 (Command Palette), 8 (Live Event Stream):", 11, "hd2")
    s.box(20, 712, 600, 50, "Item 7 / 8 event vocabulary for agreement/evidence events", "unres", sub="UNRESOLVED DG4-X1 - no frozen basis; nothing invented (Q7)", fs=11)
    s.text(20, 800, "Unchanged: 8-item Persistent Application Grammar, ten shared components, five canvas adapters, nine-step flow order.", 10, "sub2")
    return s.render("DG4 proposal vocabulary")

ORIG_RAIL = ["HOME /\nPROFILE", "MISSIONS", "COMMAND", "KA§§A", "SIG /\nRANK", "COMMS", "CIVITAS", "ECONOMY", "WORLD"]
SHELL_RAIL = [("ORIENT", "/portal /world /kingdoms"), ("FIND WORK", "/kassa /missions /bountyboard /openroles"), ("MISSION\nCONTROL", "/agentdash /dashboard /mission /slots"), ("DEPLOY", "/deploy"), ("COMMAND", "/command"), ("CAMPAIGN", "/campaign"), ("GOVERN", "/governance /senate /forums"), ("ECONOMY", "/economics /treasury /connect /earnings-matrix"), ("REFERENCE", "/vault /academia /guides /moses")]

def rails(s, x, y, w=300, label_left="ORIGINAL nine-mode rail (shell-states.png)", label_right="SHELL nine (shell.html:121-131)"):
    s.text(x, y, label_left, 12, "hd2"); s.text(x + w + 60, y, label_right, 12, "hd2")
    for i, l in enumerate(ORIG_RAIL):
        s.box(x, y + 12 + i * 44, w, 38, l.replace("\n", " "), "orig", fs=12)
    for i, (l, p) in enumerate(SHELL_RAIL):
        s.box(x + w + 60, y + 12 + i * 44, w, 38, l.replace("\n", " "), "prop", sub=p, fs=11)
    s.text(x, y + 12 + 9 * 44 + 14, "Both are nine. The sets differ. No frozen-contract clause selects between them. Q9 is OPEN - neither is picked here.", 10, "nm")

def mock_dg5():
    s = Svg(1400, 1420)
    s.text(20, 22, "PROPOSAL states and Q9 flag. Original rail/sidebar/canvas/Inspector/HUD grammar retained as master.", 12, "hd")
    rails(s, 20, 50)
    # HUD + inspector
    s.zone(760, 40, 620, 190, "HUD (DG5-U1, U2) PROPOSAL")
    s.box(776, 70, 280, 40, "acting identity | current agent (orig)", "orig", fs=10)
    s.box(1070, 70, 296, 40, "+ principal class P1-P8 | acting FOR", "prop", fs=10)
    s.text(776, 134, "Context ribbon (lens, not spine):", 10, "sub2")
    s.text(776, 150, "post > agreement/entry > slot > mission > formation > motion > settlement > Seed", 10, "sub2")
    s.text(776, 168, "keys not live render 'not carried' - never invented", 10, "nm")
    s.text(776, 200, "Ribbon is navigation only; shell grants no permissions.", 10, "sub2")
    s.zone(760, 250, 620, 330, "Inspector (DG5-U1, U3, U4) PROPOSAL")
    for i, (l, k) in enumerate([("STATE  (State Badge: intent | pending | accepted | active | completed | rejected | withdrawn | expired | terminated)", "prop"), ("AUTHORITY  (Agreement id/class or 'platform operational'; admin = operational, not standing)", "prop"), ("GOVERNANCE", "orig"), ("ECONOMY", "orig"), ("PROVENANCE", "orig")]):
        s.box(776, 280 + i * 52, 590, 44, l, k, fs=9.5)
    s.text(776, 556, "WORLD Inspector: 'entity' qualified (Entity vs Entity Node vs Ecosystem) + projection-state tag.", 10, "sub2")
    s.text(776, 572, "States: authoritative / derived / candidate / public verification (1D S7.1).", 10, "sub2")
    # town hall
    s.zone(760, 600, 620, 130, "CIVITAS caption (DG5-U5) PROPOSAL")
    s.text(776, 630, "formal governance: meetings, motions, votes, council, constitution", 11, "sub2")
    s.text(776, 650, "Town Hall = community surface, not formal governance (see D4 options on decision board).", 11, "nm")
    # control board
    s.zone(20, 530 + 220, 1360, 330, "Control Board (DG5-U6) PROPOSAL - latent / gated tiles hidden by rail compression")
    s.add('<rect x="40" y="800" width="640" height="130" rx="6" fill="none" stroke="#9a9a9a"/>')
    s.text(48, 816, "AUTHORITATIVE CORE BAND", 10, "sub2")
    for i, l in enumerate(["Agreements", "Missions", "Seeds / Audit", "Economy"]): s.box(56 + i * 154, 830, 142, 44, l + "\n(gated tile)" if l == "Agreements" else l, "prop" if l == "Agreements" else "orig", fs=10)
    s.add('<rect x="700" y="800" width="660" height="130" rx="6" fill="none" stroke="#7aa2f7"/>')
    s.text(708, 816, "DERIVED PROJECTION BAND (read-only)", 10, "sub2")
    for i, (l, k) in enumerate([("World", "orig"), ("Rank (orig SIG/RANK)", "orig"), ("Refinery\nnot implemented / gated", "nom"), ("Switchboard\nnot implemented / gated", "nom")]): s.box(716 + i * 160, 830, 150, 56, l, k, fs=9.5)
    s.text(40, 960, "Node Recognition Office: latent / gated tile (NO ORIGINAL MASTER).", 10, "nm")
    s.text(40, 980, "Rail placement of Rank/Refinery/Switchboard is UNRESOLVED (DG5-X1 / Q10): no frozen clause assigns it. Not drawn in any rail above.", 10, "nm")
    return s.render("DG5 proposal shell states")

def mock_dg6(rendered):
    s = Svg(1400, 900)
    s.text(20, 22, "PROPOSAL: per-concept delta notes. Originals are MagicPath offline previews (see embedded rendered previews above). Mocks below are annotations only.", 12, "hd")
    tiles = [
        ("KA§§A Find Work", "kassa-find-work", "U1: entry via WorkEntryAgreement; mode-dependent resolution (open/standard/constitutional)", "orig"),
        ("COMMAND / Deploy", "command-deploy", "U2: consequential preflight w/ Agreement-bound deploy authority", "orig"),
        ("World", "civitae-world", "U3: Entity / Node / Ecosystem distinction; read-only projection", "orig"),
        ("Mission Control", "mission-control", "U4: Agreement in control graph + context", "orig"),
        ("Civitas Chamber", "civitas-chamber", "U5: Town Hall vs formal governance labeling", "orig"),
        ("Shared preflight pattern", "shared-component-language", "U9: consequential preflight across concepts", "orig"),
    ]
    for i, (t, slug, note, k) in enumerate(tiles):
        x, y = 20 + (i % 3) * 460, 44 + (i // 3) * 170
        s.box(x, y, 430, 56, t + "  (original MagicPath: " + slug + ")", k, fs=10)
        s.box(x, y + 62, 430, 56, note, "prop", fs=9.5)
    s.text(20, 400, "No original master - concepts that must be authored offline or deferred (Q11):", 13, "hd2")
    nm = [("Rank / Refinery", "DG6-U6 OWNER DECISION. Read-only derived projection. Boundary level only."), ("Switchboard", "DG6-U7 OWNER DECISION. Read-only derived routing/suggestion. Boundary level only."), ("Enterprise / Entity", "DG6-U8 OWNER DECISION. Entity, Entity Node, Enterprise domain, Recognition Office.")]
    for i, (t, n) in enumerate(nm):
        x = 20 + i * 460
        s.box(x, 420, 430, 160, t + "\nNO ORIGINAL MASTER - not approved", "nom", sub=n, fs=13)
    s.text(20, 610, "These three tiles are placeholders (hatched). They carry no provenance authority and are not approved assets.", 11, "nm")
    s.text(20, 632, "Refinery/Switchboard may only be shown as PROPOSAL read-only boundary depictions (see DG1 page).", 11, "sub2")
    s.text(20, 680, "DG6-X1: inspect updates in offline prototypes only. No MagicPath, Figma, or image-generation service was used.", 11, "sub2")
    return s.render("DG6 concept deltas")

# ---------------------------------------------------------------- acceptance criteria
def ac(group, rows):
    return [{"id": f"AC-{group}-{i+1:02d}", "text": t, "items": it} for i, (t, it) in enumerate(rows)]

COMMON = [("Every proposed element carries a visible PROPOSAL / PROVISIONAL marking and the page states P2_FINAL is PENDING (owner sign-off).", [])]
ACS = {
 "DG1": ac("DG1", COMMON + [
    ("All 10 Agreement classes appear, named exactly as 1A S5.11 registry.", ["DG1-U1"]),
    ("No edge connects a Post/Opportunity node directly to a Slot/Role node without WorkEntryAgreement.", ["DG1-U2"]),
    ("WorkEntryAgreement shows Open / Standard / Constitutional chips on one node; governance edge says 'Constitutional mode only'.", ["DG1-U3"]),
    ("Entity, Entity Node, Ecosystem are three separate nodes; Root Seed and Secondary Seeds are two separate nodes.", ["DG1-U4"]),
    ("Node Recognition Office is a node distinct from Town Hall; no edge makes Town Hall an authority source.", ["DG1-U5"]),
    ("Enterprise chain shows all nine steps in order and the parent override edge; Enterprise Entity Node is labelled NO ORIGINAL MASTER.", ["DG1-U6"]),
    ("Refinery and Switchboard have inbound-only edges and are labelled NO ORIGINAL MASTER - not approved; no input/output edges invented.", ["DG1-U7", "DG1-X1"]),
    ("Governance boundary line excludes Town Hall and Forums; admin key edge reads 'operational, not standing'.", ["DG1-U8"]),
    ("No label claims 'commitment weight'.", []),
    ("Original nine zones and PLATFORM/CONNECTION cluster are shown unchanged (reviewer overlays the original PNG sha 91d70965...).", [])]),
 "DG2": ac("DG2", COMMON + [
    ("Spine order reads opportunity > entry intent > Agreement > mission/work > slot/formation > governed execution.", ["DG2-U1"]),
    ("Open/Standard/Constitutional branch present; resolver/timeout detail absent (DG2-X1).", ["DG2-U2", "DG2-X1"]),
    ("Governance gate is attached only to consequential transitions, not to every edge.", ["DG2-U3"]),
    ("Delivery / acceptance / settlement is drawn with an evidence-class chip.", ["DG2-U4"]),
    ("Failure path writes no success Seed.", ["DG2-U5"]),
    ("World, Tier/Leaderboard, Refinery, Switchboard take inbound arrows only.", ["DG2-U6"]),
    ("Context ribbon is drawn as a separate lens, not as the spine; 'motion' and 'settlement' keys flagged OWNER DECISION.", ["DG2-U7", "DG2-X1"])]),
 "DG3": ac("DG3", COMMON + [
    ("WorkEntry states (intent, pending, accepted, active) precede MissionDraft/FormationOpen; original states retained.", ["DG3-U1"]),
    ("Formation and MissionWork Agreement gates sit on existing transitions.", ["DG3-U2"]),
    ("Governance gates drawn per-transition, not per-phase.", ["DG3-U3"]),
    ("DeliveryEvidenceClass chip on Review / deliverable-ready.", ["DG3-U4"]),
    ("Receipt + Seed after Settlement; failure writes no Seed.", ["DG3-U5"]),
    ("rejected / expired / withdrawn / disputed shown; placement flagged as owner decision (Q6).", ["DG3-U6"]),
    ("Escrow precondition is NOT drawn as an existing capability (mechanism pending); depiction is owner decision (Q5).", ["DG3-X1"])]),
 "DG4": ac("DG4", COMMON + [
    ("Nine-step flow unchanged and in original order.", ["DG4-U4"]),
    ("Principal step names the 8 principal classes without conflating credential with principal.", ["DG4-U1"]),
    ("Breadcrumb shows Agreement as an optional segment and distinguishes Entity from Entity Node.", ["DG4-U2"]),
    ("Value Strip separates treasury / escrow / stake.", ["DG4-U3"]),
    ("World/Refinery/Switchboard adapters show no commit/write control.", ["DG4-U5"]),
    ("Action Stack caption states verb-row and consent-class inheritance.", ["DG4-U6"]),
    ("Command Palette / Live Event Stream event vocabulary is left UNRESOLVED, not invented.", ["DG4-X1"]),
    ("All original shared components and adapters retained; vocabulary changes additive.", [])]),
 "DG5": ac("DG5", COMMON + [
    ("Rail has the original nine modes or the owner-approved set per Q9 - both are displayed, neither chosen.", ["DG5-U7"]),
    ("HUD and Inspector show principal class and acting-for.", ["DG5-U1"]),
    ("Agreement/WorkEntry badge uses 1A S4.1 / S5.2 state names.", ["DG5-U3", "DG5-U2"]),
    ("Entity, Entity Node, Ecosystem distinguished in WORLD.", ["DG5-U4"]),
    ("Town Hall is not shown as formal governance anywhere.", ["DG5-U5"]),
    ("Control Board shows latent/gated systems with authoritative vs derived bands.", ["DG5-U6"]),
    ("Inspector groups STATE / AUTHORITY / GOVERNANCE / ECONOMY / PROVENANCE.", ["DG5-U1"]),
    ("Rank/Refinery/Switchboard rail placement is NOT assigned (UNRESOLVED DG5-X1).", ["DG5-X1"]),
    ("No shell element implies it grants permissions.", [])]),
 "DG6": ac("DG6", COMMON + [
    ("KA§§A concept note shows entry via WorkEntryAgreement with mode-dependent resolution.", ["DG6-U1"]),
    ("COMMAND concept note shows consequential preflight with Agreement-bound deploy authority.", ["DG6-U2"]),
    ("World concept note separates Entity / Node / Ecosystem and marks projection read-only.", ["DG6-U3"]),
    ("Mission Control note places Agreement in control graph and context.", ["DG6-U4"]),
    ("Civitas note labels Town Hall distinct from formal governance.", ["DG6-U5"]),
    ("Rank/Refinery, Switchboard, Enterprise/Entity tiles are hatched and read NO ORIGINAL MASTER - not approved.", ["DG6-U6", "DG6-U7", "DG6-U8"]),
    ("Preflight pattern is consistent across concepts.", ["DG6-U9"]),
    ("Updates are inspected in offline prototypes only (no external service).", ["DG6-X1"])]),
}

# ---------------------------------------------------------------- html
CSS = """
:root{--bg:#0f1115;--fg:#e8e8e8;--mut:#9aa0a6;--amb:#f5a623;--red:#e5484d;--blu:#7aa2f7;--card:#171a21;--line:#2a2f3a}
@media (prefers-color-scheme:light){:root{--bg:#f6f6f4;--fg:#1a1a1a;--mut:#555;--card:#fff;--line:#d6d6d6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,system-ui,sans-serif}
main{max-width:1240px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:.3em 0}h2{font-size:17px;margin:1.6em 0 .4em;border-bottom:1px solid var(--line);padding-bottom:4px}
.banner{background:#3a2a05;color:#ffd58a;border:1px solid var(--amb);padding:10px 12px;border-radius:6px;font-weight:600}
.red{background:#3a1114;color:#ffb3b6;border-color:var(--red)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:10px 0}
code,.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px;word-break:break-all}
.scroll{overflow:auto;border:1px solid var(--line);border-radius:6px;background:#000;max-height:70vh}
.scroll img{display:block;max-width:none}
svg.mock{width:100%;height:auto;background:#12141a;border:1px solid var(--line);border-radius:6px}
.o{fill:#1b1b1b;stroke:#8a8a8a}.p{fill:#2a2208;stroke:#f5a623;stroke-dasharray:6 3;stroke-width:1.6}
.n{fill:url(#hatch);stroke:#e5484d;stroke-dasharray:4 3;stroke-width:1.6}.r{fill:#0f1a2e;stroke:#7aa2f7;stroke-dasharray:6 3;stroke-width:1.6}
.u{fill:#2a1114;stroke:#e5484d;stroke-dasharray:2 3;stroke-width:1.6}
.zone{fill:none;stroke-width:1.2}.pz{stroke:#f5a623;stroke-dasharray:3 4}.rz{stroke:#7aa2f7;stroke-dasharray:3 4}
svg text{fill:#e8e8e8;font-family:-apple-system,system-ui,sans-serif}.zt,.hd{fill:#f5a623;font-weight:700}.hd2{fill:#e8e8e8;font-weight:700}
.sub,.sub2,.al{fill:#a8adb4}.nm{fill:#ff8a8f;font-weight:600}.lg{fill:#e8e8e8}
.ap{stroke:#f5a623;stroke-width:1.6;stroke-dasharray:5 3}.ao{stroke:#9a9a9a;stroke-width:1.6}.ar{stroke:#7aa2f7;stroke-width:1.6;stroke-dasharray:5 3}.au{stroke:#e5484d;stroke-width:1.6;stroke-dasharray:2 3}
table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top;font-size:13px}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:700;border:1px solid}
.PROPOSED{color:var(--amb)}.UNRESOLVED{color:var(--red)}.OWNER{color:var(--blu)}
ul.ac{list-style:none;padding:0}ul.ac li{padding:6px 0;border-bottom:1px solid var(--line)}
ul.ac label{margin-right:10px;font-size:12px}nav a{margin-right:12px;color:var(--blu)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
details summary{cursor:pointer}
@media (max-width:600px){main{padding:12px}}
"""
JS = """
<script>
(function(){var K='p2vr:'+document.body.dataset.page;var st={};try{st=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
document.querySelectorAll('input[type=radio]').forEach(function(r){if(st[r.name]===r.value)r.checked=true;
r.addEventListener('change',function(){st[r.name]=r.value;try{localStorage.setItem(K,JSON.stringify(st))}catch(e){}})})})();
</script>"""
NAV = '<nav><a href="index.html">Decision board</a>' + "".join(f'<a href="{g}.html">{g}</a>' for g in ["DG1", "DG2", "DG3", "DG4", "DG5", "DG6"]) + "</nav>"
BANNER = ('<div class="banner">PROVISIONAL / PROPOSAL ONLY. P2_FINAL is PENDING: the owner must view these pages and sign off. '
          'Nothing here is approved, attested, or a replacement for the original FigJam / MagicPath masters. Frozen Phase 1 contracts 1A-1G are the authority and are unmodified.</div>')

def page(title, body, key):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{E(title)}</title><style>{CSS}</style></head><body data-page="{key}"><main>{NAV}{BANNER}<h1>{E(title)}</h1>{body}{JS}</main></body></html>')

def master_block(gid):
    rows = ""
    for m in GROUPS[gid]["master_refs"]:
        rows += f'<tr><td class="mono">{E(m["path"])}</td><td class="mono">{m["sha256"]}</td></tr>'
    return f'<table><tr><th>Master file (read-only, under {E(str(CW))}/)</th><th>sha256</th></tr>{rows}</table>'

def items_table(gid):
    rows = ""
    for it in ITEMS[gid]:
        st = it["status"]; cl = "UNRESOLVED" if "UNRES" in st else ("OWNER" if "OWNER" in st else "PROPOSED")
        cites = "<br>".join(f'{c["contract"]} {E(c["section"])}' for c in it["cites"]) or "NONE (no frozen basis; nothing invented)"
        ch = "<br>".join(f'[{t}] {E(x)}' for t, x in it["changes"])
        rows += f'<tr><td class="mono">{it["id"]}</td><td>{E(it["title"])}<div class="mono">{ch}</div></td><td><span class="tag {cl}">{E(st)}</span></td><td>{cites}</td></tr>'
    return f'<table><tr><th>Item</th><th>Delta / change list</th><th>Status</th><th>Frozen-contract basis (heading cited)</th></tr>{rows}</table>'

def ac_block(gid):
    out = '<ul class="ac">'
    for a in ACS[gid]:
        its = (" <span class=mono>[" + ", ".join(a["items"]) + "]</span>") if a["items"] else ""
        out += (f'<li><b class="mono">{a["id"]}</b> {E(a["text"])}{its}<br>'
                + "".join(f'<label><input type="radio" name="{a["id"]}" value="{v}"> {v}</label>' for v in ("PASS", "FAIL", "N/A")) + '</li>')
    return out + "</ul><p class='mono'>Pass/fail selections are stored only in this browser (localStorage) as a reviewer convenience; they are not an attestation.</p>"

def group_page(gid, mock_svg, master_html, extra=""):
    g = GROUPS[gid]
    body = (f'<p>Group <b>{gid}</b> - {E(g["artifact"])}. Spec: <code>workflows/signomy/out/p2-delta-specs/{g["spec_file"]}</code></p>'
            f'<div class="card"><b>PRESERVE:</b> {E(g["preserve"])}<br><b>REQUIRED UPDATE:</b> {E(g["update_required"])}</div>'
            f'<h2>1. Original master</h2>{master_html}'
            f'<h2>2. Proposed delta (annotated mock) - PROPOSAL</h2>{legend_svg()}{mock_svg}{extra}'
            f'<h2>3. Delta items and frozen-contract basis</h2>{items_table(gid)}'
            f'<h2>4. Testable visual acceptance criteria</h2>{ac_block(gid)}'
            f'<h2>5. Status</h2><p>P2_FINAL: <b>PENDING</b> - owner must view and sign off. This page is review evidence only.</p>')
    return body

def img_block(path, width, caption, maxh=None):
    uri, (w, h) = data_uri(path, width)
    return (f'<div class="card"><b>{E(caption)}</b><div class="mono">{E(str(path).replace(str(CW)+"/", "$CW/"))}<br>master sha256: {sha(path)}<br>'
            f'Embedded preview: downscaled to {w}x{h} (display derivative only - the master file is unchanged). Scroll/zoom; open the master itself for full resolution.</div>'
            f'<div class="scroll"><img src="{uri}" width="{w}" height="{h}" alt="{E(caption)}"></div></div>')

def build():
    pages, manifest_pages = {}, []
    def register(gid, fname, masters, supplementary=()):
        cites = []
        seen = set()
        for it in ITEMS[gid]:
            for c in it["cites"]:
                k = (c["contract"], c["section"])
                if k not in seen: seen.add(k); cites.append(c)
        manifest_pages.append({"id": gid, "file": fname, "title": GROUPS[gid]["artifact"],
            "masters": masters, "supplementary_display_files": list(supplementary), "master_missing": [],
            "cited_contract_headings": cites, "acceptance_criteria": [a["id"] for a in ACS[gid]],
            "delta_items": {it["id"]: it["status"] for it in ITEMS[gid]}})
    def mref(gid): return [{"path": m["path"], "sha256": m["sha256"]} for m in GROUPS[gid]["master_refs"]]

    # DG1
    mh = master_block("DG1") + img_block(D2 / "system-interaction-map.png", 2400, "system-interaction-map.png (original FigJam master, downscaled preview)")
    pages["DG1.html"] = page("DG1 - System Interaction Map: master vs proposal", group_page("DG1", mock_dg1(), mh), "DG1")
    register("DG1", "DG1.html", mref("DG1"))
    # DG2
    mh = master_block("DG2") + img_block(D2 / "operational-spine.png", 2000, "operational-spine.png (original master, downscaled preview)")
    pages["DG2.html"] = page("DG2 - Operational Spine: master vs proposal", group_page("DG2", mock_dg2(), mh), "DG2")
    register("DG2", "DG2.html", mref("DG2"))
    # DG3
    mh = master_block("DG3") + img_block(D2 / "mission-lifecycle.png", 1000, "mission-lifecycle.png (original master, downscaled preview; tall)")
    pages["DG3.html"] = page("DG3 - Mission Lifecycle: master vs proposal", group_page("DG3", mock_dg3(), mh), "DG3")
    register("DG3", "DG3.html", mref("DG3"))
    # DG4
    mh = master_block("DG4") + img_block(D2 / "unified-control-grammar.png", 1800, "unified-control-grammar.png (original master, downscaled preview)")
    pages["DG4.html"] = page("DG4 - Unified Control Grammar: master vs proposal", group_page("DG4", mock_dg4(), mh), "DG4")
    register("DG4", "DG4.html", mref("DG4"))
    # DG5
    mh = (master_block("DG5") + img_block(D2 / "shell-states.png", 2400, "shell-states.png (original nine-mode rail master, downscaled preview)")
          + img_block(D2 / "canonical-board-page-1-overview.png", 2400, "canonical-board-page-1-overview.png (original)"))
    extra = ('<div class="card red banner">Q9 FLAG (OWNER DECISION, not resolved here): the original nine-mode rail and the shell nine are different sets. '
             'Both are shown side by side in the mock above. This review does not pick one.</div>')
    pages["DG5.html"] = page("DG5 - Shell States and Control Board: master vs proposal", group_page("DG5", mock_dg5(), mh, extra), "DG5")
    register("DG5", "DG5.html", mref("DG5"))
    # DG6
    rend = {}
    mh = master_block("DG6") + '<h3>Rendered previews of the MagicPath concepts (supplementary display files, hashed below)</h3><div class="grid">'
    supp = []
    for slug, cap in [("kassa-find-work", "KA§§A Find Work"), ("command-deploy", "COMMAND / Deploy"), ("civitae-world", "World"), ("mission-control", "Mission Control"), ("civitas-chamber", "Civitas Chamber"), ("shared-component-language", "Shared component language")]:
        p = MP / slug / "rendered-preview.png"; uri, (w, h) = data_uri(p, 640)
        rp = str(p).replace(str(CW) + "/", ""); supp.append({"path": rp, "sha256": sha(p), "note": "rendered-preview.png: display derivative of the offline-preview.html master; not in the P2 baseline inventory"})
        mh += f'<div class="card"><b>{E(cap)}</b><div class="mono">{E(rp)}<br>sha256 {sha(p)}</div><img src="{uri}" alt="{E(cap)}" style="width:100%;height:auto"></div>'
    mh += "</div>"
    extra = ('<div class="card red banner">NO ORIGINAL MASTER - not approved: Rank/Refinery, Switchboard, Enterprise/Entity Node. '
             'Placeholders in the mock are hatched and carry no provenance authority. Q11 (author offline / wait / defer) is an owner decision.</div>')
    pages["DG6.html"] = page("DG6 - High-fidelity MagicPath concepts: master vs proposal", group_page("DG6", mock_dg6(rend), mh, extra), "DG6")
    register("DG6", "DG6.html", mref("DG6"), supp)

    pages["index.html"] = page("P2 owner preview / decision board", board(manifest_pages), "index")

    for f, h in pages.items(): (OUT / f).write_text(h)
    manifest = {
        "status": "PROVISIONAL", "p2_final": "PENDING - owner must view and sign off",
        "statement": "Offline review evidence only. No new architecture semantics. Originals remain visual master.",
        "control_workspace_root": str(CW),
        "frozen_contracts": {k: {"file": v["file"], "sha256": v["sha256"]} for k, v in spec["contracts"].items()},
        "decision_board": {"file": "index.html", "cited_contract_headings": BOARD_CITES, "acceptance_criteria": [a["id"] for a in BOARD_ACS]},
        "pages": manifest_pages,
        "no_original_master": ["Rank/Refinery", "Switchboard", "Enterprise Entity Node"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print("wrote", len(pages), "pages")

BOARD_CITES = [
    {"contract": "1G", "file": "reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md", "section": "§5.E Governance verbs"},
    {"contract": "1B", "file": "reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md", "section": "§1 Load-bearing invariants"},
    {"contract": "1D", "file": "reports/phase-1/PHASE-1D-ENTITY-NODE.md", "section": "§0 Canonical invariants (non-compressible)"},
    {"contract": "1A", "file": "reports/phase-1/PHASE-1A-AGREEMENT-STACK.md", "section": "§2 Canonical ordering"},
]
BOARD_ACS = ac("BOARD", [
    ("Decision board states the frozen rule 'Town Hall != formal Governance' and cites 1G S5.E.", []),
    ("D4 shows 2-3 placement options, recommends COMMS separation, and creates NO tenth primary mode.", []),
    ("D4 is shown as HELD: /forums is not moved by this work.", []),
    ("Q9 shows both nine-mode rails side by side and picks neither.", []),
    ("Rank/Refinery, Switchboard, Enterprise Entity Node are listed as NO ORIGINAL MASTER - not approved.", []),
    ("P2_FINAL is stated as PENDING owner sign-off.", [])])

def d4_option(title, rec, lines, extra_cls="p"):
    s = Svg(420, 250)
    s.add(f'<rect class="zone" x="4" y="4" width="412" height="242" rx="8" stroke="#555"/>')
    s.text(14, 24, title, 12, "hd2")
    for i, (l, k) in enumerate(lines): s.box(14, 36 + i * 36, 392, 30, l, k, fs=10)
    return s.render(title)

def board(mp):
    o = ('<h2>Page index</h2><table><tr><th>Group</th><th>Page</th><th>Original master</th><th>Items (P / U / OD)</th></tr>')
    miss = {"DG6": "present for 5 concepts + shared language; MISSING for Rank/Refinery, Switchboard, Enterprise Entity Node"}
    for p in mp:
        st = list(p["delta_items"].values())
        c = lambda k: sum(1 for x in st if k in x)
        o += (f'<tr><td>{p["id"]}</td><td><a href="{p["file"]}">{E(p["title"])}</a></td><td>{miss.get(p["id"], "FOUND (hash verified by check script)")}</td>'
              f'<td>{c("PROPOSED")} / {c("UNRESOLVED")} / {c("OWNER")}</td></tr>')
    o += "</table>"
    o += ('<h2>NO ORIGINAL MASTER - not approved</h2><div class="card red banner">Rank/Refinery, Switchboard and Enterprise Entity Node have no original FigJam/MagicPath master. '
          'They appear only as hatched PROPOSAL placeholders at boundary level, read-only, with no provenance authority. Nothing is invented as approved.</div>')
    o += ('<h2>D4 (HELD): Town Hall / Forums placement</h2>'
          '<div class="card"><b>Frozen rule:</b> Town Hall != formal Governance (1G &sect;5.E Governance verbs; also 1B &sect;1 I-9 and 1D &sect;0). '
          'Town Hall is discussion / petition / deliberation / notice; formal governance is meeting / motion / vote / constitutional action. '
          '<br><b>Held:</b> <code>/forums</code> is NOT moved out of GOVERN by this work (<code>frontend/shell.html:128</code> untouched) and NO tenth primary mode is created. '
          'The original high-fidelity visual vocabulary stays the provisional master. (Naming note: this "D4" is the shell-rail correction in CLAUDE-TAKEOVER-2026-10-11.md; it is unrelated to 1B "D4 Financial standing".)</div>')
    o1 = d4_option("Option 1 (RECOMMENDED) - COMMS separation", True, [("GOVERN: Governance | Senate | Meetings | Motions | Votes | Constitution", "orig"), ("COMMS: Inbox | Threads | Mission | Forums | Town Hall", "prop"), ("Town Hall -> Recognition Office: petition link only", "prop"), ("No tenth mode; nine rail slots unchanged", "orig")])
    o2 = d4_option("Option 2 - COMMS home + labelled cross-link", False, [("GOVERN: formal governance only", "orig"), ("COMMS: Forums + Town Hall (canonical home)", "prop"), ("GOVERN sidebar: 'Community surface (not governance)' link", "prop"), ("Cross-link visually outside the governance boundary", "orig")])
    o3 = d4_option("Option 3 - Keep in GOVERN, annotate (status quo)", False, [("GOVERN: Governance | Senate | Forums", "orig"), ("Boundary line: Forums outside formal-governance box", "prop"), ("Caption: 'Town Hall = community surface, not governance'", "prop"), ("Weakest: shell.html:128 conflicts with shell.html:120 comment", "unres")])
    o += f'<div class="grid"><div>{o1}</div><div>{o2}</div><div>{o3}</div></div>'
    o += ('<p><b>Recommendation:</b> Option 1 (COMMS separation). The original COMMS mode already hosts Town Hall in its Left/Tabs (shell-states.png); the original CIVITAS mode lists Town Hall beside formal governance objects, which is the visual ambiguity the frozen rule forbids. '
          'This is a recommendation for the owner; the placement decision (Q8 / D4) is the owner\'s and stays HELD.</p>')
    s = Svg(900, 580); rails(s, 14, 20, 400)
    o += ('<h2>Q9 FLAG: original nine-mode rail vs shell nine (side by side, no pick)</h2>'
          '<div class="card red banner">Q9 is an OWNER DECISION. Left: original rail from shell-states.png (HOME...WORLD). Right: shell rail from shell.html:121-131 (ORIENT...REFERENCE). No frozen clause selects between them; navigation consolidation != semantic consolidation.</div>'
          + s.render("Q9 rails"))
    o += '<h2>Owner decisions and questions (from INDEX.md)</h2><ul>'
    for q in spec["owner_questions"]: o += f"<li>{E(q)}</li>"
    o += '</ul><h2>Decision-board acceptance criteria</h2>'
    o += '<ul class="ac">' + "".join(f'<li><b class="mono">{a["id"]}</b> {E(a["text"])}<br>' + "".join(f'<label><input type="radio" name="{a["id"]}" value="{v}"> {v}</label>' for v in ("PASS", "FAIL", "N/A")) + "</li>" for a in BOARD_ACS) + "</ul>"
    o += ('<h2>Sign-off</h2><div class="card">P2_FINAL: <b>PENDING</b>. The owner must view these pages and sign off. Not attested here; roadmap receipts untouched. '
          'Run <code>python3 workflows/signomy/out/p2-visual-review/tools/check_p2_visual_review.py</code> for heading/hash verification.</div>')
    return o

if __name__ == "__main__":
    build()
