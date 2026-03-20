import React, { useState } from "react";

const GOLD = "#C4923A";
const DARK = "#0a0a0f";
const PANEL = "#111118";
const BORDER = "#1e1e2a";
const MUTED = "#6a6a8a";
const WHITE = "#e8e8f0";
const BLUE = "#4a7fff";
const GREEN = "#3ddc84";
const RED = "#ff4a6a";
const PURPLE = "#a78bfa";
const CYAN = "#22d3ee";
const ORANGE = "#f59e0b";

const nodes = [
  {
    id: "frontend",
    label: "COMMAND\nFrontend",
    x: 400, y: 60,
    color: GOLD,
    desc: "Your existing HTML. Controls governance, displays execution. Both input and output.",
    gov: "Governance controls (mode, posture, profile, vault loader, COMMAND bar, presets)",
    exec: "WebSocket connection to server, real-time message display, session hash display",
    files: "index.html (~200 lines of changes to existing)"
  },
  {
    id: "server",
    label: "Server\nCore",
    x: 400, y: 200,
    color: BLUE,
    desc: "FastAPI + WebSocket hub. The switchboard. Every component talks through this.",
    gov: "Stores governance state, broadcasts governance changes to MCP bridge",
    exec: "WebSocket broadcast, REST endpoints, static file serving, session management",
    files: "app.py (~300 lines) + run.py (~50 lines)"
  },
  {
    id: "context",
    label: "Context\nAssembler",
    x: 160, y: 340,
    color: GOLD,
    desc: "THE CORE. Builds the governed payload agents actually see. Doesn't exist in agentchattr at all. This is your IP at the code level.",
    gov: "Reads governance mode → translates to behavioral constraints. Reads posture → translates to response parameters. Reads user profile → translates to calibration. Reads vault → packages relevant docs.",
    exec: "Called by MCP bridge on every chat_read. Assembles the full context object.",
    files: "context.py (~250 lines) — NEW, no equivalent anywhere"
  },
  {
    id: "store",
    label: "Message\nStore",
    x: 640, y: 200,
    color: GREEN,
    desc: "JSONL persistence. But messages carry governance metadata — not raw text.",
    gov: "Every message stamped with active governance mode, posture, loaded vault docs at time of send",
    exec: "Append-only JSONL, load on startup, observer callbacks for real-time broadcast",
    files: "store.py (~100 lines)"
  },
  {
    id: "sequence",
    label: "Sequence\nEngine",
    x: 160, y: 200,
    color: PURPLE,
    desc: "Governance-aware routing. Not @mention parsing — constitutional ordering.",
    gov: "Primary responds first under full governance. Secondary reads Primary's response + governance. Observer reads both + governance but cannot initiate.",
    exec: "Determines next agent, checks if previous in sequence has responded, enforces loop limits",
    files: "sequence.py (~120 lines)"
  },
  {
    id: "mcp",
    label: "MCP\nBridge",
    x: 400, y: 460,
    color: CYAN,
    desc: "Agent-facing tools. This is where governance becomes real — every read is governed.",
    gov: "chat_read calls Context Assembler → agents get constitutional context, not raw messages",
    exec: "FastMCP server on port 8200. Tools: chat_send, chat_read, chat_join, chat_who",
    files: "mcp_bridge.py (~200 lines)"
  },
  {
    id: "vault",
    label: "Vault\nEngine",
    x: 640, y: 340,
    color: ORANGE,
    desc: "Document store. Protocols, personas, prompts — loaded into context assembly.",
    gov: "Documents carry categories (Protocol, Persona, Prompt). Category determines injection behavior.",
    exec: "File storage, metadata tracking, selection state synced with frontend",
    files: "vault.py (~150 lines)"
  },
  {
    id: "audit",
    label: "Audit\nSpine",
    x: 50, y: 460,
    color: RED,
    desc: "Runs through EVERYTHING. Every state change, every message, every config change — hashed and logged.",
    gov: "Session fingerprint (config hash), content integrity (message hash), governance change log",
    exec: "SHA-256 hashing, append-only audit log, DOI anchor point",
    files: "audit.py (~100 lines)"
  },
  {
    id: "agents",
    label: "AI\nAgents",
    x: 400, y: 590,
    color: MUTED,
    desc: "Claude Code, Codex, Gemini, any MCP-compatible agent. They connect, they read governed context, they respond under constitutional control.",
    gov: "Receive: governance mode, posture constraints, vault context, role assignment, sequence position",
    exec: "Connect via MCP, call chat_read/chat_send, operate within governed parameters",
    files: "External — no code needed, they connect to your MCP endpoint"
  }
];

const connections = [
  { from: "frontend", to: "server", label: "WebSocket\n+ REST", bidirectional: true },
  { from: "server", to: "store", label: "persist\n+ broadcast", bidirectional: true },
  { from: "server", to: "sequence", label: "who's\nnext?", bidirectional: true },
  { from: "server", to: "context", label: "gov state\n+ vault", bidirectional: false },
  { from: "context", to: "mcp", label: "governed\npayload", bidirectional: false },
  { from: "context", to: "vault", label: "load\ndocs", bidirectional: true },
  { from: "mcp", to: "agents", label: "MCP\ntools", bidirectional: true },
  { from: "store", to: "audit", label: "every\nmessage", bidirectional: false },
  { from: "server", to: "audit", label: "every\nchange", bidirectional: false },
  { from: "sequence", to: "mcp", label: "trigger\norder", bidirectional: false },
  { from: "mcp", to: "store", label: "agent\nmessages", bidirectional: false },
];

function getNodeCenter(node) {
  return { x: node.x, y: node.y };
}

function Arrow({ from, to, label, bidirectional }) {
  const f = nodes.find(n => n.id === from);
  const t = nodes.find(n => n.id === to);
  if (!f || !t) return null;
  
  const fc = getNodeCenter(f);
  const tc = getNodeCenter(t);
  
  const dx = tc.x - fc.x;
  const dy = tc.y - fc.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const nx = dx / dist;
  const ny = dy / dist;
  
  const startX = fc.x + nx * 48;
  const startY = fc.y + ny * 36;
  const endX = tc.x - nx * 48;
  const endY = tc.y - ny * 36;
  
  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2;

  return (
    <g>
      <line x1={startX} y1={startY} x2={endX} y2={endY}
        stroke={BORDER} strokeWidth={1.5} strokeDasharray="4,4" />
      <circle cx={endX} cy={endY} r={3} fill={MUTED} />
      {bidirectional && <circle cx={startX} cy={startY} r={3} fill={MUTED} />}
      {label && (
        <text x={midX} y={midY} textAnchor="middle" fill={MUTED}
          style={{ fontSize: "9px", fontFamily: "monospace" }}>
          {label.split("\n").map((line, i) => (
            <tspan key={i} x={midX} dy={i === 0 ? 0 : 11}>{line}</tspan>
          ))}
        </text>
      )}
    </g>
  );
}

function Node({ node, isSelected, onClick }) {
  const r = 44;
  return (
    <g onClick={() => onClick(node.id)} style={{ cursor: "pointer" }}>
      <circle cx={node.x} cy={node.y} r={r + 4}
        fill="none" stroke={isSelected ? node.color : "transparent"} strokeWidth={2}
        opacity={0.6} />
      <circle cx={node.x} cy={node.y} r={r}
        fill={PANEL} stroke={node.color} strokeWidth={1.5} />
      <text x={node.x} y={node.y} textAnchor="middle" fill={WHITE}
        style={{ fontSize: "11px", fontWeight: 600, fontFamily: "monospace" }}>
        {node.label.split("\n").map((line, i) => (
          <tspan key={i} x={node.x} dy={i === 0 ? -6 : 14}>{line}</tspan>
        ))}
      </text>
    </g>
  );
}

function DetailPanel({ node }) {
  if (!node) return (
    <div style={{
      padding: "24px", color: MUTED, fontFamily: "monospace", fontSize: "13px",
      lineHeight: 1.6
    }}>
      Click any node to see how governance and execution weave through it.
    </div>
  );

  return (
    <div style={{ padding: "20px", fontFamily: "monospace", fontSize: "12px", lineHeight: 1.7 }}>
      <div style={{ 
        fontSize: "16px", fontWeight: 700, color: node.color, 
        marginBottom: "8px", letterSpacing: "0.5px" 
      }}>
        {node.label.replace("\n", " ")}
      </div>
      
      <div style={{ color: WHITE, marginBottom: "16px", fontSize: "13px" }}>
        {node.desc}
      </div>

      <div style={{
        background: `${GOLD}12`, border: `1px solid ${GOLD}30`,
        borderRadius: "6px", padding: "12px", marginBottom: "10px"
      }}>
        <div style={{ color: GOLD, fontWeight: 700, marginBottom: "6px", fontSize: "11px", letterSpacing: "1px" }}>
          § GOVERNANCE DIMENSION
        </div>
        <div style={{ color: "#d4d4e8" }}>{node.gov}</div>
      </div>

      <div style={{
        background: `${CYAN}12`, border: `1px solid ${CYAN}30`,
        borderRadius: "6px", padding: "12px", marginBottom: "10px"
      }}>
        <div style={{ color: CYAN, fontWeight: 700, marginBottom: "6px", fontSize: "11px", letterSpacing: "1px" }}>
          ⚡ EXECUTION DIMENSION
        </div>
        <div style={{ color: "#d4d4e8" }}>{node.exec}</div>
      </div>

      <div style={{
        background: `${MUTED}12`, border: `1px solid ${MUTED}30`,
        borderRadius: "6px", padding: "12px"
      }}>
        <div style={{ color: MUTED, fontWeight: 700, marginBottom: "6px", fontSize: "11px", letterSpacing: "1px" }}>
          FILE
        </div>
        <div style={{ color: "#d4d4e8" }}>{node.files}</div>
      </div>
    </div>
  );
}

export default function COMMANDArchitecture() {
  const [selected, setSelected] = useState(null);
  const selectedNode = nodes.find(n => n.id === selected);

  return (
    <div style={{
      background: DARK, minHeight: "100vh", display: "flex", flexDirection: "column",
      fontFamily: "monospace", color: WHITE
    }}>
      <div style={{
        padding: "16px 24px", borderBottom: `1px solid ${BORDER}`,
        display: "flex", alignItems: "baseline", gap: "16px"
      }}>
        <span style={{ color: GOLD, fontWeight: 700, fontSize: "16px", letterSpacing: "1px" }}>
          COMMAND ARCHITECTURE
        </span>
        <span style={{ color: MUTED, fontSize: "12px" }}>
          Governance × Execution — not layered, woven
        </span>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <svg viewBox="0 0 800 660" style={{ width: "100%", height: "100%" }}>
            <defs>
              <radialGradient id="glow">
                <stop offset="0%" stopColor={GOLD} stopOpacity="0.08" />
                <stop offset="100%" stopColor={GOLD} stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect width="800" height="660" fill={DARK} />
            
            {/* Governance / Execution dimension labels */}
            <text x="30" y="30" fill={GOLD} opacity="0.3" style={{ fontSize: "10px", letterSpacing: "2px" }}>
              § GOVERNANCE
            </text>
            <text x="680" y="30" fill={CYAN} opacity="0.3" style={{ fontSize: "10px", letterSpacing: "2px" }}>
              ⚡ EXECUTION
            </text>

            {/* Subtle glow behind context assembler */}
            <circle cx={160} cy={340} r={90} fill="url(#glow)" />

            {connections.map((c, i) => (
              <Arrow key={i} {...c} />
            ))}
            {nodes.map(n => (
              <Node key={n.id} node={n} isSelected={selected === n.id}
                onClick={setSelected} />
            ))}

            {/* Legend */}
            <g transform="translate(600, 520)">
              <text x={0} y={0} fill={MUTED} style={{ fontSize: "10px", letterSpacing: "1px" }}>
                TOTAL NEW CODE
              </text>
              <text x={0} y={18} fill={WHITE} style={{ fontSize: "11px" }}>
                7 files · ~1,270 lines
              </text>
              <text x={0} y={36} fill={MUTED} style={{ fontSize: "10px" }}>
                + ~200 lines JS changes
              </text>
              <text x={0} y={56} fill={MUTED} style={{ fontSize: "10px" }}>
                to existing index.html
              </text>
              
              <text x={0} y={86} fill={GOLD} style={{ fontSize: "10px" }}>
                § = only in COMMAND
              </text>
              <text x={0} y={102} fill={CYAN} style={{ fontSize: "10px" }}>
                ⚡ = commodity (any framework)
              </text>
              <text x={0} y={118} fill={PURPLE} style={{ fontSize: "10px" }}>
                ◈ = governance transforms commodity
              </text>
            </g>
          </svg>
        </div>

        <div style={{
          width: "340px", borderLeft: `1px solid ${BORDER}`,
          background: PANEL, overflowY: "auto"
        }}>
          <DetailPanel node={selectedNode} />
          
          {!selectedNode && (
            <div style={{ padding: "0 24px 24px", fontFamily: "monospace" }}>
              <div style={{ 
                color: GOLD, fontSize: "12px", fontWeight: 700, 
                marginBottom: "12px", letterSpacing: "1px" 
              }}>
                WHY IT'S WOVEN
              </div>
              
              {[
                {
                  title: "Message flows through governance",
                  detail: "User sends → governance wraps it → sequence engine routes it → MCP delivers governed context → agent reads constitutional orders → agent responds → response logged with governance metadata → audit hashes everything"
                },
                {
                  title: "Governance flows through execution",
                  detail: "Mode changes in UI → server broadcasts → Context Assembler rebuilds payload → next agent read gets new constraints → agent behavior shifts in real-time. No restart, no re-deploy."
                },
                {
                  title: "Audit flows through everything",
                  detail: "Every message, every governance change, every vault load, every posture adjustment, every agent join — hashed, timestamped, logged. The audit spine doesn't sit on top. It runs through every component."
                },
                {
                  title: "Context Assembly is the core",
                  detail: "Not the server. Not the MCP bridge. The Context Assembler is where governance becomes execution. It reads mode + posture + vault + profile + messages and builds the single object agents see. This component doesn't exist anywhere else."
                }
              ].map((item, i) => (
                <div key={i} style={{ 
                  marginBottom: "14px", padding: "10px",
                  background: `${BORDER}80`, borderRadius: "4px"
                }}>
                  <div style={{ color: WHITE, fontSize: "11px", fontWeight: 600, marginBottom: "4px" }}>
                    {item.title}
                  </div>
                  <div style={{ color: MUTED, fontSize: "10px", lineHeight: 1.5 }}>
                    {item.detail}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
