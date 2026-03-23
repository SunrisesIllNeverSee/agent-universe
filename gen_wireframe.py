#!/usr/bin/env python3
"""CIVITAE — proper hierarchy tree, depth reflects actual navigation structure"""

import json, random, os

E = []
def uid(): return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',k=20))

def dot(cx, cy, r, fill, stroke):
    E.append({"id":uid(),"type":"ellipse","x":cx-r,"y":cy-r,"width":r*2,"height":r*2,
        "angle":0,"strokeColor":stroke,"backgroundColor":fill,"fillStyle":"solid",
        "strokeWidth":1.5,"strokeStyle":"solid","roughness":1,"opacity":100,
        "groupIds":[],"frameId":None,"roundness":{"type":2},
        "seed":random.randint(1,2**31),"version":1,"versionNonce":random.randint(1,2**31),
        "isDeleted":False,"boundElements":[],"updated":1711000000000,"link":None,"locked":False})

def ln(x1,y1,x2,y2,stroke="#CED4DA",sw=1.2,dashed=False):
    E.append({"id":uid(),"type":"line","x":x1,"y":y1,"width":x2-x1,"height":y2-y1,
        "angle":0,"strokeColor":stroke,"backgroundColor":"transparent","fillStyle":"solid",
        "strokeWidth":sw,"strokeStyle":"dashed" if dashed else "solid","roughness":0,"opacity":70,
        "groupIds":[],"frameId":None,"roundness":None,
        "seed":random.randint(1,2**31),"version":1,"versionNonce":random.randint(1,2**31),
        "isDeleted":False,"boundElements":[],"updated":1711000000000,"link":None,"locked":False,
        "points":[[0,0],[x2-x1,y2-y1]],"lastCommittedPoint":None})

def label(cx, cy, name, route, size, color, muted):
    w = max(len(name)*size*0.6, 20)
    E.append({"id":uid(),"type":"text","x":cx-w/2,"y":cy+12,"width":w,"height":size*1.4,
        "angle":0,"strokeColor":color,"backgroundColor":"transparent","fillStyle":"solid",
        "strokeWidth":1,"strokeStyle":"solid","roughness":1,"opacity":100,
        "groupIds":[],"frameId":None,"roundness":None,
        "seed":random.randint(1,2**31),"version":1,"versionNonce":random.randint(1,2**31),
        "isDeleted":False,"boundElements":[],"updated":1711000000000,"link":None,"locked":False,
        "text":name,"fontSize":size,"fontFamily":1,"textAlign":"center",
        "verticalAlign":"top","containerId":None,"originalText":name,"lineHeight":1.25,
        "baseline":int(size*0.9)})
    if route:
        rw = max(len(route)*9*0.58, 20)
        E.append({"id":uid(),"type":"text","x":cx-rw/2,"y":cy+12+size*1.4,"width":rw,"height":11*1.4,
            "angle":0,"strokeColor":muted,"backgroundColor":"transparent","fillStyle":"solid",
            "strokeWidth":1,"strokeStyle":"solid","roughness":1,"opacity":100,
            "groupIds":[],"frameId":None,"roundness":None,
            "seed":random.randint(1,2**31),"version":1,"versionNonce":random.randint(1,2**31),
            "isDeleted":False,"boundElements":[],"updated":1711000000000,"link":None,"locked":False,
            "text":route,"fontSize":9,"fontFamily":2,"textAlign":"center",
            "verticalAlign":"top","containerId":None,"originalText":route,"lineHeight":1.25,
            "baseline":9})

# ── Colors ────────────────────────────────────────────────────────────────────
GOLD="#C4923A"; LIVE="#2F9E44"; WIP="#F59F00"; EMPTY="#C92A2A"
ROOT_C="#12151A"; HUB_C="#1C7ED6"; SEC_C="#6741D9"; MUTED="#ADB5BD"

# ── Tree definition ───────────────────────────────────────────────────────────
# Each node: (name, route, status, color_override, [children])
# status: "live" | "wip" | "empty" | "hub" | "root" | "sec"

TREE = ("CIVITAE", "/", "root", ROOT_C, [

    ("World Map", "/", "live", None, [
        ("Entry / Signup", "/entry", "live", None, []),
    ]),

    ("Missions Hub", "/missions", "hub", HUB_C, [
        ("Mission Detail",  "/mission",      "wip",   None, []),
        ("Governance",      "/governance",   "live",  None, [
            ("Meeting & Vote",  "/governance#mtg", "live", None, []),
        ]),
        ("Economics",       "/economics",    "wip",   None, [
            ("KA§§A",       "/kassa",        "wip",   None, []),
            ("Vault",       "/vault",        "empty", None, []),
        ]),
        ("Leaderboard",     "/leaderboard",  "wip",   None, []),
        ("Help Wanted",     "/helpwanted",   "live",  None, []),
        ("Bounty Board",    "/bountyboard",  "wip",   None, []),
        ("Slots",           "/slots",        "wip",   None, []),
        ("Agent Profile",   "/agent/me",     "wip",   None, [
            ("Dashboard",   "/dashboard",    "wip",   None, []),
            ("Campaign",    "/campaign",     "wip",   None, []),
        ]),
        ("Territory",       "", "sec", SEC_C, [
            ("Kingdoms",    "/kingdoms",     "wip",   None, []),
            ("Civitae Map", "/civitae-map",  "wip",   None, []),
        ]),
    ]),

    ("Meta", "", "sec", SEC_C, [
        ("Roadmap",         "/civitae-roadmap", "wip",   None, []),
        ("Wave Registry",   "/wave-registry",   "empty", None, []),
        ("Refinery",        "/refinery",        "empty", None, []),
        ("Switchboard",     "/switchboard",     "empty", None, []),
        ("Admin",           "/admin",           "wip",   None, []),
    ]),
])

# ── Layout algorithm ──────────────────────────────────────────────────────────
LEAF_W  = 108
LEVEL_H = 110

def count_leaves(node):
    _, _, _, _, children = node
    if not children:
        return 1
    return sum(count_leaves(c) for c in children)

def assign_positions(node, x_offset, depth):
    name, route, status, color_override, children = node
    leaves = count_leaves(node)
    cx = x_offset + (leaves * LEAF_W) / 2
    cy = 60 + depth * LEVEL_H
    node_with_pos = (name, route, status, color_override, children, cx, cy)

    placed_children = []
    child_x = x_offset
    for child in children:
        placed = assign_positions(child, child_x, depth + 1)
        placed_children.append(placed)
        child_x += count_leaves(child) * LEAF_W

    return (name, route, status, color_override, placed_children, cx, cy)

def draw_tree(node, parent_cx=None, parent_cy=None):
    name, route, status, color_override, children, cx, cy = node

    # Line from parent
    if parent_cx is not None:
        ln(parent_cx, parent_cy + 8, cx, cy - 8, stroke="#CED4DA", sw=1.2)

    # Node color
    if color_override:
        fill = stroke = color_override
        r = 10 if status in ("root","hub","sec") else 7
    else:
        c = {"live":LIVE,"wip":WIP,"empty":EMPTY}.get(status, MUTED)
        fill = stroke = c
        r = 7

    # Font size by depth
    if status == "root":      fs, fc = 16, GOLD
    elif status in ("hub","sec"): fs, fc = 13, color_override
    else:                     fs, fc = 11, "#212529"

    dot(cx, cy, r, fill, stroke)
    label(cx, cy, name, route if status not in ("root","sec","hub") else "", fs, fc, MUTED)

    for child in children:
        draw_tree(child, cx, cy)

# ── Render ────────────────────────────────────────────────────────────────────
placed = assign_positions(TREE, 40, 0)
draw_tree(placed)

# ── Legend ────────────────────────────────────────────────────────────────────
total_w = count_leaves(TREE) * LEAF_W + 80
LX = total_w + 20; LY = 60
items = [("Live", LIVE), ("WIP / needs polish", WIP), ("Empty placeholder", EMPTY),
         ("Hub / section node", HUB_C), ("Sub-section", SEC_C)]
for i,(t,c) in enumerate(items):
    dot(LX+8, LY+14+i*26, 6, c, c)
    w = max(len(t)*10*0.58,20)
    E.append({"id":uid(),"type":"text","x":LX+20,"y":LY+7+i*26,"width":w,"height":14,
        "angle":0,"strokeColor":"#495057","backgroundColor":"transparent","fillStyle":"solid",
        "strokeWidth":1,"strokeStyle":"solid","roughness":1,"opacity":100,
        "groupIds":[],"frameId":None,"roundness":None,
        "seed":random.randint(1,2**31),"version":1,"versionNonce":random.randint(1,2**31),
        "isDeleted":False,"boundElements":[],"updated":1711000000000,"link":None,"locked":False,
        "text":t,"fontSize":10,"fontFamily":2,"textAlign":"left",
        "verticalAlign":"top","containerId":None,"originalText":t,"lineHeight":1.25,"baseline":9})

# ── Export ────────────────────────────────────────────────────────────────────
out = {"type":"excalidraw","version":2,"source":"https://excalidraw.com",
       "elements":E,"appState":{"gridSize":None,"viewBackgroundColor":"#FFFFFF"},"files":{}}
path = os.path.expanduser("~/Desktop/civitae-wireframe.excalidraw")
with open(path,"w") as f: json.dump(out,f,indent=2)
print(f"✅  {len(E)} elements  →  {path}")
