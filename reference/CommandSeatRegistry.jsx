import { useState, useEffect, useCallback } from "react";

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════

const toRoman = (n) => {
  const map = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",8:"VIII",
    9:"IX",10:"X",11:"XI",12:"XII",13:"XIII",14:"XIV",15:"XV",16:"XVI",17:"XVII"};
  return map[n] || String(n);
};

const toSup = (n) => {
  const sup = ["⁰","¹","²","³","⁴","⁵","⁶","⁷","⁸","⁹"];
  return String(n).split("").map(d => sup[parseInt(d)]).join("");
};

const seatLabel = (id, transferCount) =>
  `C${toRoman(id)}${transferCount > 0 ? toSup(transferCount) : ""}`;

const stepOf = (wave) => ({ "1a": 1, "1b": 2, "2a": 3, "2b": 4, "3": null }[wave]);

const fmt = (n) => n ? `$${n.toLocaleString()}` : "—";
const fmtShort = (n) => {
  if (!n) return "—";
  if (n >= 1000000) return `$${(n/1000000).toFixed(2)}M`;
  return `$${(n/1000).toFixed(0)}K`;
};

// ═══════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════

const INITIAL_SEATS = [
  { id:1,  wave:"1a", tier:"Internal", basePrice:65000,  owner:null, ownerEntity:null, status:"AVAILABLE", signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:2,  wave:"1a", tier:"Internal", basePrice:65000,  owner:null, ownerEntity:null, status:"AVAILABLE", signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:3,  wave:"1a", tier:"Internal", basePrice:65000,  owner:null, ownerEntity:null, status:"AVAILABLE", signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:4,  wave:"1a", tier:"Internal", basePrice:65000,  owner:null, ownerEntity:null, status:"AVAILABLE", signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:5,  wave:"1a", tier:"Internal", basePrice:65000,  owner:null, ownerEntity:null, status:"AVAILABLE", signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:6,  wave:"1b", tier:"Embedded", basePrice:130000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:7,  wave:"1b", tier:"Embedded", basePrice:130000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:8,  wave:"1b", tier:"Embedded", basePrice:130000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:9,  wave:"2a", tier:"Internal", basePrice:195000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:10, wave:"2a", tier:"Internal", basePrice:195000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:11, wave:"2a", tier:"Internal", basePrice:195000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:12, wave:"2a", tier:"Internal", basePrice:195000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:13, wave:"2a", tier:"Internal", basePrice:195000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:14, wave:"2b", tier:"Embedded", basePrice:260000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:15, wave:"2b", tier:"Embedded", basePrice:260000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:16, wave:"2b", tier:"Embedded", basePrice:260000, owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
  { id:17, wave:"3",  tier:"Bid",      basePrice:null,   owner:null, ownerEntity:null, status:"LOCKED",    signal:null, lastSalePrice:null, lastSaleDate:null, transferCount:0 },
];

const CASCADE_GATES = [
  { trigger:[1,2,3,4,5],     unlocks:[6,7,8],           label:"CW1a → CW1b" },
  { trigger:[6,7,8],         unlocks:[9,10,11,12,13],   label:"CW1b → CW2a" },
  { trigger:[9,10,11,12,13], unlocks:[14,15,16],         label:"CW2a → CW2b" },
  { trigger:[14,15,16],      unlocks:[17],               label:"CW2b → CW3"  },
];

const WAVES = [
  { key:"1a", label:"CW1a", name:"Wave 1a", sub:"Internal",  step:1, accent:"#1a6b4a" },
  { key:"1b", label:"CW1b", name:"Wave 1b", sub:"Embedded",  step:2, accent:"#1a5a6b" },
  { key:"2a", label:"CW2a", name:"Wave 2a", sub:"Internal",  step:3, accent:"#6b5a1a" },
  { key:"2b", label:"CW2b", name:"Wave 2b", sub:"Embedded",  step:4, accent:"#6b2a1a" },
  { key:"3",  label:"CW3",  name:"Wave 3",  sub:"Bid",       step:null, accent:"#4a2a6b" },
];

const SEAT17_TERMS = [
  "Bid only — no fixed price",
  "Note lineage required (hash-verified)",
  "Past or present note holders qualify",
  "Product transfers with seat on sale",
  "MO§ES™ core architecture excluded",
  "Royalty on downstream revenue — rate negotiated",
  "Minimum deployment threshold required",
  "Reversion clause on inactivity",
];

// ═══════════════════════════════════════════
// APP
// ═══════════════════════════════════════════

export default function CommandSeatRegistry() {
  const [seats, setSeats] = useState(INITIAL_SEATS);
  const [view, setView] = useState("board");
  const [selectedId, setSelectedId] = useState(null);
  const [adminAuth, setAdminAuth] = useState(false);
  const [adminPin, setAdminPin] = useState("");
  const [inquiries, setInquiries] = useState([]);
  const [form, setForm] = useState({});
  const [adminForm, setAdminForm] = useState({});
  const [adminEditing, setAdminEditing] = useState(null);
  const [toast, setToast] = useState(null);
  const [showExplainer, setShowExplainer] = useState(false);
  const [transferSeatId, setTransferSeatId] = useState(null);

  const applyCascade = useCallback((data) => {
    const u = data.map(s => ({...s}));
    CASCADE_GATES.forEach(g => {
      if (g.trigger.every(id => u.find(s => s.id === id)?.status === "TAKEN")) {
        g.unlocks.forEach(id => {
          const s = u.find(x => x.id === id);
          if (s && s.status === "LOCKED") s.status = "AVAILABLE";
        });
      }
    });
    return u;
  }, []);

  useEffect(() => { setSeats(prev => applyCascade(prev)); }, [applyCascade]);

  const notify = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3500); };

  const selected = seats.find(s => s.id === selectedId);
  const filled = seats.filter(s => s.status === "TAKEN" || s.status === "RETIRED").length;
  const revenue = seats.reduce((a, s) => a + (s.lastSalePrice || 0), 0);
  const activeWave = (() => {
    for (const w of ["1a","1b","2a","2b","3"]) {
      if (seats.filter(s => s.wave === w).some(s => s.status === "AVAILABLE")) return w;
    }
    return "1a";
  })();

  const recordSale = (id) => {
    setSeats(prev => {
      const u = prev.map(s => s.id === id ? {
        ...s, owner: adminForm.owner, ownerEntity: adminForm.entity,
        status: "TAKEN", signal: adminForm.signal || "ACCEPTING_INQUIRIES",
        lastSalePrice: parseInt(adminForm.price) || s.basePrice,
        lastSaleDate: new Date().toISOString().split("T")[0],
      } : s);
      return applyCascade(u);
    });
    setAdminEditing(null); setAdminForm({});
    notify(`${seatLabel(id, seats.find(s=>s.id===id)?.transferCount||0)} — sale confirmed`);
  };

  const recordTransfer = (id) => {
    setSeats(prev => prev.map(s => {
      if (s.id === id) {
        const newCount = s.transferCount + 1;
        return { ...s, owner: adminForm.owner, ownerEntity: adminForm.entity,
          signal: adminForm.signal || "ACCEPTING_INQUIRIES",
          lastSalePrice: parseInt(adminForm.price) || s.lastSalePrice,
          lastSaleDate: new Date().toISOString().split("T")[0],
          transferCount: newCount };
      }
      return s;
    }));
    setTransferSeatId(null); setAdminForm({});
    notify(`${seatLabel(id, (seats.find(s=>s.id===id)?.transferCount||0)+1)} — transfer recorded`);
  };

  const updateSeat = (id) => {
    setSeats(prev => prev.map(s => s.id === id ? {
      ...s, owner: adminForm.owner || s.owner,
      ownerEntity: adminForm.entity || s.ownerEntity,
      signal: adminForm.signal || s.signal,
    } : s));
    setAdminEditing(null);
    notify(`${seatLabel(id, seats.find(s=>s.id===id)?.transferCount||0)} — updated`);
  };

  const submitInquiry = () => {
    if (!form.company || !form.email) return;
    setInquiries(prev => [...prev, {
      id: Date.now(), seatId: selectedId,
      company: form.company, email: form.email, message: form.message || "",
      timestamp: new Date().toISOString(), status: "NEW",
    }]);
    setForm({}); setView("detail");
    notify(`Inquiry submitted for ${seatLabel(selectedId, selected?.transferCount||0)}`);
  };

  // ═══════════════════════════════════════════
  // STYLES
  // ═══════════════════════════════════════════

  const font = "'Söhne','Suisse Intl','Helvetica Neue',Helvetica,sans-serif";
  const mono = "'Söhne Mono','IBM Plex Mono','Menlo',monospace";

  const c = {
    bg:"#fafaf8", surface:"#ffffff", surfaceAlt:"#f5f5f2",
    border:"#e8e6e1", borderLight:"#f0eee9",
    text:"#1a1a18", textSec:"#6b6960", textTer:"#9b978e",
    accent:"#1a1a18",
    green:"#1a6b4a", greenBg:"#e8f5ee",
    amber:"#8b6914", amberBg:"#fef9e7",
    red:"#8b2020", redBg:"#fef0f0",
    blue:"#1a4a6b", blueBg:"#e8f0f5",
    purple:"#4a2a6b", purpleBg:"#f0e8f5",
  };

  const tierColor = (tier) => tier === "Internal" ? c.green : tier === "Embedded" ? c.blue : c.purple;
  const tierBg = (tier) => tier === "Internal" ? c.greenBg : tier === "Embedded" ? c.blueBg : c.purpleBg;
  const statusColor = (st) => st === "AVAILABLE" ? c.green : st === "TAKEN" ? c.red : c.textTer;

  const base = {
    app:{ minHeight:"100vh", background:c.bg, color:c.text, fontFamily:font, fontSize:"14px", lineHeight:"1.55" },
    header:{ padding:"20px 28px", display:"flex", justifyContent:"space-between", alignItems:"center", borderBottom:`1px solid ${c.border}`, background:c.surface },
    logo:{ fontSize:"11px", fontFamily:mono, letterSpacing:"3px", fontWeight:600, color:c.text, textTransform:"uppercase" },
    logosub:{ fontSize:"10px", fontFamily:mono, letterSpacing:"1.5px", color:c.textTer, marginTop:"2px" },
    nav:{ display:"flex", gap:"4px" },
    navBtn:(active) => ({ padding:"7px 16px", fontSize:"11px", fontFamily:mono, letterSpacing:"0.5px", background:active?c.text:"transparent", color:active?c.surface:c.textSec, border:`1px solid ${active?c.text:c.border}`, cursor:"pointer", borderRadius:"3px", transition:"all 0.15s ease" }),
    stats:{ padding:"12px 28px", display:"flex", gap:"28px", borderBottom:`1px solid ${c.borderLight}`, background:c.surface, fontSize:"11px", fontFamily:mono },
    statLabel:{ color:c.textTer, letterSpacing:"0.5px" },
    statVal:{ color:c.text, fontWeight:600, marginLeft:"6px" },
    content:{ padding:"28px" },
    // Board grid — individual cards
    boardGrid:{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(160px, 1fr))", gap:"12px" },
    waveSection:{ marginBottom:"32px" },
    waveHeader:{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:"12px", paddingBottom:"8px", borderBottom:`1px solid ${c.border}` },
    waveLabel:{ fontSize:"12px", fontFamily:mono, fontWeight:600, letterSpacing:"1.5px", textTransform:"uppercase" },
    waveStep:{ fontSize:"10px", fontFamily:mono, color:c.textTer },
    waveFill:{ fontSize:"11px", fontFamily:mono, color:c.textTer },
    // Seat card
    seatCard:(status) => ({
      background:c.surface, border:`1px solid ${status==="AVAILABLE"?c.border:status==="TAKEN"?"#c8c0b8":c.borderLight}`,
      borderRadius:"4px", padding:"18px 16px", cursor:status==="LOCKED"?"default":"pointer",
      opacity:status==="LOCKED"?0.45:1, transition:"all 0.15s ease",
      position:"relative", overflow:"hidden",
    }),
    seatCardAccent:(tier) => ({
      position:"absolute", top:0, left:0, right:0, height:"2px",
      background:tierColor(tier),
    }),
    seatId:{ fontSize:"22px", fontWeight:700, color:c.text, marginBottom:"2px", fontFamily:mono, letterSpacing:"-0.5px" },
    seatStep:{ fontSize:"9px", fontFamily:mono, color:c.textTer, letterSpacing:"1px", marginBottom:"10px" },
    seatPrice:(tier) => ({ fontSize:"14px", fontWeight:600, color:tierColor(tier), marginBottom:"4px" }),
    seatStatus:(status) => ({ fontSize:"9px", fontFamily:mono, letterSpacing:"1px", color:statusColor(status), textTransform:"uppercase" }),
    seatSignal:{ fontSize:"8px", fontFamily:mono, color:c.textTer, marginTop:"3px" },
    gate:(open) => ({
      textAlign:"center", padding:"8px 12px", fontSize:"10px", fontFamily:mono,
      color:open?c.green:c.textTer, letterSpacing:"1px",
      background:open?c.greenBg:"transparent", borderRadius:"3px",
      margin:"0 0 12px", border:`1px solid ${open?c.green:c.borderLight}`,
    }),
    // Detail
    detail:{ maxWidth:"520px", margin:"0 auto" },
    back:{ fontSize:"11px", fontFamily:mono, color:c.textSec, cursor:"pointer", marginBottom:"20px", display:"inline-flex", alignItems:"center", gap:"6px" },
    detailId:{ fontSize:"36px", fontWeight:700, color:c.text, fontFamily:mono, letterSpacing:"-1px" },
    detailMeta:{ display:"flex", gap:"12px", marginTop:"4px", marginBottom:"24px", flexWrap:"wrap" },
    badge:(bg,fg) => ({ display:"inline-block", padding:"3px 10px", fontSize:"10px", fontFamily:mono, letterSpacing:"0.5px", background:bg, color:fg, borderRadius:"2px" }),
    row:{ display:"flex", justifyContent:"space-between", padding:"11px 0", borderBottom:`1px solid ${c.borderLight}`, fontSize:"13px" },
    rowLabel:{ color:c.textSec, fontSize:"11px", fontFamily:mono },
    rowVal:{ color:c.text, fontWeight:500 },
    btn:(bg,fg,border) => ({ width:"100%", padding:"13px", marginTop:"12px", background:bg||"transparent", border:`1px solid ${border||c.text}`, color:fg||c.text, fontSize:"11px", fontFamily:mono, letterSpacing:"1.5px", textTransform:"uppercase", cursor:"pointer", borderRadius:"3px", transition:"all 0.15s ease" }),
    termsBox:{ margin:"20px 0", padding:"16px 18px", background:c.purpleBg, border:`1px solid #d8cce5`, borderRadius:"4px", fontSize:"12px", lineHeight:"1.7" },
    formGroup:{ marginBottom:"14px" },
    label:{ display:"block", fontSize:"10px", fontFamily:mono, letterSpacing:"0.5px", color:c.textSec, marginBottom:"5px", textTransform:"uppercase" },
    input:{ width:"100%", padding:"10px 12px", background:c.surfaceAlt, border:`1px solid ${c.border}`, color:c.text, fontSize:"13px", fontFamily:font, borderRadius:"3px", outline:"none", boxSizing:"border-box" },
    textarea:{ width:"100%", padding:"10px 12px", background:c.surfaceAlt, border:`1px solid ${c.border}`, color:c.text, fontSize:"13px", fontFamily:font, borderRadius:"3px", outline:"none", minHeight:"80px", resize:"vertical", boxSizing:"border-box" },
    select:{ width:"100%", padding:"10px 12px", background:c.surfaceAlt, border:`1px solid ${c.border}`, color:c.text, fontSize:"13px", fontFamily:font, borderRadius:"3px", outline:"none", boxSizing:"border-box" },
    adminRow:(locked) => ({ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"10px 18px", borderBottom:`1px solid ${c.borderLight}`, opacity:locked?0.35:1, fontSize:"12px" }),
    adminBtn:(accent) => ({ padding:"5px 12px", fontSize:"10px", fontFamily:mono, background:"transparent", border:`1px solid ${accent||c.border}`, color:accent||c.textSec, borderRadius:"2px", cursor:"pointer", marginLeft:"6px" }),
    adminForm:{ padding:"14px 18px", background:c.surfaceAlt, borderBottom:`1px solid ${c.border}` },
    adminFormRow:{ display:"flex", gap:"10px", flexWrap:"wrap", alignItems:"flex-end" },
    overlay:{ position:"fixed", top:0, left:0, right:0, bottom:0, background:"rgba(0,0,0,0.4)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:"24px" },
    modal:{ background:c.surface, border:`1px solid ${c.border}`, borderRadius:"6px", padding:"32px", maxWidth:"580px", width:"100%", maxHeight:"85vh", overflow:"auto", boxShadow:"0 20px 60px rgba(0,0,0,0.12)" },
    modalTitle:{ fontSize:"13px", fontFamily:mono, fontWeight:600, letterSpacing:"1.5px", textTransform:"uppercase", marginBottom:"20px", color:c.text },
    modalClose:{ marginTop:"24px", padding:"10px 24px", background:"transparent", border:`1px solid ${c.border}`, color:c.textSec, fontSize:"11px", fontFamily:mono, cursor:"pointer", borderRadius:"3px" },
    toast:{ position:"fixed", bottom:"24px", right:"24px", background:c.surface, border:`1px solid ${c.green}`, color:c.green, padding:"12px 20px", fontSize:"11px", fontFamily:mono, borderRadius:"4px", zIndex:2000, boxShadow:"0 4px 12px rgba(0,0,0,0.08)" },
    footer:{ padding:"20px 28px", borderTop:`1px solid ${c.border}`, fontSize:"10px", fontFamily:mono, color:c.textTer, textAlign:"center", letterSpacing:"1px" },
  };

  // ═══════════════════════════════════════════
  // BOARD
  // ═══════════════════════════════════════════

  const renderBoard = () => (
    <div style={base.content}>
      {WAVES.map((w) => {
        const wSeats = seats.filter(s => s.wave === w.key);
        const gate = CASCADE_GATES.find(g => g.unlocks.includes(wSeats[0]?.id));
        const gateOpen = !gate || gate.trigger.every(id => seats.find(s => s.id === id)?.status === "TAKEN");
        const filledInWave = wSeats.filter(s => s.status === "TAKEN").length;

        return (
          <div key={w.key} style={base.waveSection}>
            {gate && (
              <div style={base.gate(gateOpen)}>
                {gateOpen ? `✓ Gate open — ${gate.label}` : `○ Locked — ${gate.label}`}
              </div>
            )}
            <div style={base.waveHeader}>
              <div style={{display:"flex", alignItems:"baseline", gap:"12px"}}>
                <span style={base.waveLabel}>{w.label}</span>
                <span style={{fontSize:"11px", color:c.textTer, fontFamily:mono}}>{w.sub}</span>
                {w.step && <span style={{fontSize:"9px", fontFamily:mono, color:c.textTer, letterSpacing:"1px"}}>STEP {w.step}</span>}
              </div>
              <span style={base.waveFill}>{filledInWave}/{wSeats.length}</span>
            </div>
            <div style={base.boardGrid}>
              {wSeats.map(seat => (
                <div
                  key={seat.id}
                  style={base.seatCard(seat.status)}
                  onClick={() => { if (seat.status !== "LOCKED") { setSelectedId(seat.id); setView("detail"); }}}
                  onMouseEnter={e => { if (seat.status !== "LOCKED") e.currentTarget.style.background = c.surfaceAlt; }}
                  onMouseLeave={e => { e.currentTarget.style.background = c.surface; }}
                >
                  <div style={base.seatCardAccent(seat.tier)} />
                  <div style={base.seatId}>{seatLabel(seat.id, seat.transferCount)}</div>
                  {w.step && <div style={base.seatStep}>STEP {w.step} · {seat.wave.toUpperCase()}</div>}
                  <div style={base.seatPrice(seat.tier)}>
                    {seat.lastSalePrice ? fmtShort(seat.lastSalePrice) : seat.id === 17 ? "BID" : fmtShort(seat.basePrice)}
                  </div>
                  <div style={base.seatStatus(seat.status)}>{seat.status}</div>
                  {seat.signal && seat.status === "TAKEN" && (
                    <div style={base.seatSignal}>{seat.signal.replace(/_/g," ").toLowerCase()}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );

  // ═══════════════════════════════════════════
  // DETAIL
  // ═══════════════════════════════════════════

  const renderDetail = () => {
    if (!selected) return null;
    const w = WAVES.find(x => x.key === selected.wave);
    const label = seatLabel(selected.id, selected.transferCount);
    return (
      <div style={{...base.content, ...base.detail}}>
        <div style={base.back} onClick={() => setView("board")}>← Registry</div>
        <div style={base.detailId}>{label}</div>
        <div style={base.detailMeta}>
          <span style={base.badge(tierBg(selected.tier), tierColor(selected.tier))}>{selected.tier}</span>
          <span style={base.badge(c.surfaceAlt, c.textSec)}>{w.label}</span>
          {w.step && <span style={base.badge(c.surfaceAlt, c.textTer)}>Step {w.step}</span>}
          {selected.transferCount > 0 && <span style={base.badge(c.amberBg, c.amber)}>{selected.transferCount} Transfer{selected.transferCount>1?"s":""}</span>}
        </div>

        <div style={base.row}><span style={base.rowLabel}>Status</span><span style={{...base.rowVal, color:statusColor(selected.status)}}>{selected.status}</span></div>
        <div style={base.row}><span style={base.rowLabel}>Tier</span><span style={base.rowVal}>{selected.tier}</span></div>
        <div style={base.row}><span style={base.rowLabel}>Wave</span><span style={base.rowVal}>{w.label} — {w.sub}</span></div>
        {w.step && <div style={base.row}><span style={base.rowLabel}>Step</span><span style={base.rowVal}>{w.step} of 4</span></div>}
        {selected.transferCount > 0 && <div style={base.row}><span style={base.rowLabel}>Transfers</span><span style={base.rowVal}>{selected.transferCount}</span></div>}
        {selected.id !== 17 && <div style={base.row}><span style={base.rowLabel}>Entry Price</span><span style={{...base.rowVal, color:tierColor(selected.tier)}}>{fmt(selected.basePrice)}</span></div>}
        {selected.lastSalePrice && <div style={base.row}><span style={base.rowLabel}>Last Confirmed Sale</span><span style={{...base.rowVal, fontWeight:700}}>{fmt(selected.lastSalePrice)}</span></div>}
        {selected.lastSaleDate && <div style={base.row}><span style={base.rowLabel}>Sale Date</span><span style={base.rowVal}>{selected.lastSaleDate}</span></div>}
        {selected.owner && <div style={base.row}><span style={base.rowLabel}>Holder</span><span style={base.rowVal}>{selected.owner}</span></div>}
        {selected.signal && selected.status === "TAKEN" && <div style={base.row}><span style={base.rowLabel}>Signal</span><span style={{...base.rowVal, color:c.blue}}>{selected.signal.replace(/_/g," ")}</span></div>}

        {selected.id === 17 && selected.status === "AVAILABLE" && (
          <div style={base.termsBox}>
            <div style={{fontSize:"10px", fontFamily:mono, letterSpacing:"1px", color:c.purple, marginBottom:"10px", fontWeight:600}}>CXVII — BID TERMS</div>
            {SEAT17_TERMS.map((t,i) => <div key={i} style={{padding:"2px 0", color:c.textSec}}>{t}</div>)}
            <div style={{marginTop:"8px", fontSize:"11px", color:c.textTer, fontStyle:"italic"}}>All terms subject to negotiation.</div>
          </div>
        )}

        {selected.status === "AVAILABLE" && (
          <button style={base.btn(c.text, c.surface, c.text)} onClick={() => setView("inquiry")}>
            {selected.id === 17 ? "Submit Bid Inquiry" : "Inquire About This Seat"}
          </button>
        )}
        {selected.status === "TAKEN" && selected.signal === "ACCEPTING_INQUIRIES" && (
          <button style={base.btn("transparent", c.blue, c.blue)} onClick={() => setView("inquiry")}>Contact Seat Holder</button>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════════
  // INQUIRY
  // ═══════════════════════════════════════════

  const renderInquiry = () => {
    if (!selected) return null;
    return (
      <div style={{...base.content, ...base.detail}}>
        <div style={base.back} onClick={() => setView("detail")}>← {seatLabel(selected.id, selected.transferCount)}</div>
        <div style={{fontSize:"13px", fontFamily:mono, letterSpacing:"1px", marginBottom:"24px", color:c.textSec, textTransform:"uppercase"}}>
          {selected.status === "TAKEN" ? "Contact Seat Holder" : `Inquire — ${seatLabel(selected.id, selected.transferCount)}`}
        </div>
        <div style={base.formGroup}><label style={base.label}>Company Name *</label><input style={base.input} value={form.company||""} onChange={e=>setForm({...form,company:e.target.value})} /></div>
        <div style={base.formGroup}><label style={base.label}>Contact Email *</label><input style={base.input} type="email" value={form.email||""} onChange={e=>setForm({...form,email:e.target.value})} /></div>
        <div style={base.formGroup}><label style={base.label}>Intended Use Case</label><textarea style={base.textarea} value={form.message||""} onChange={e=>setForm({...form,message:e.target.value})} /></div>
        {selected.id === 17 && <div style={base.formGroup}><label style={base.label}>Bid Amount</label><input style={base.input} type="number" value={form.bid||""} onChange={e=>setForm({...form,bid:e.target.value})} /></div>}
        <button style={base.btn(c.text, c.surface, c.text)} onClick={submitInquiry}>Submit Inquiry</button>
        <button style={{...base.btn(), marginTop:"8px"}} onClick={() => setView("detail")}>Cancel</button>
        <div style={{marginTop:"16px", fontSize:"11px", color:c.textTer, lineHeight:"1.6"}}>All negotiations happen offline. Ello Cello LLC will respond directly to your inquiry. No transactions are processed through this interface.</div>
      </div>
    );
  };

  // ═══════════════════════════════════════════
  // ADMIN
  // ═══════════════════════════════════════════

  const renderAdmin = () => {
    if (!adminAuth) {
      return (
        <div style={{...base.content, maxWidth:"320px", margin:"0 auto"}}>
          <div style={{fontSize:"11px", fontFamily:mono, color:c.textSec, marginBottom:"16px", letterSpacing:"1px", textTransform:"uppercase"}}>Admin Access</div>
          <div style={base.formGroup}><label style={base.label}>PIN</label><input style={base.input} type="password" value={adminPin} onChange={e=>setAdminPin(e.target.value)} onKeyDown={e=>{ if(e.key==="Enter" && adminPin==="1234") setAdminAuth(true); }} /></div>
          <button style={base.btn(c.text,c.surface,c.text)} onClick={() => { if(adminPin==="1234") setAdminAuth(true); }}>Authenticate</button>
        </div>
      );
    }

    return (
      <div style={base.content}>
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"20px"}}>
          <div style={{fontSize:"11px", fontFamily:mono, letterSpacing:"1.5px", color:c.textSec, textTransform:"uppercase"}}>Admin — Seat Registry</div>
          <button style={base.adminBtn()} onClick={() => { setAdminAuth(false); setAdminPin(""); }}>Sign out</button>
        </div>
        <div style={{background:c.surface, border:`1px solid ${c.border}`, borderRadius:"4px", overflow:"hidden"}}>
          {seats.map(seat => {
            const label = seatLabel(seat.id, seat.transferCount);
            const isEditing = adminEditing === seat.id;
            const isTransfer = transferSeatId === seat.id;
            return (
              <div key={seat.id}>
                <div style={base.adminRow(seat.status==="LOCKED")}>
                  <div style={{display:"flex", alignItems:"center", gap:"12px"}}>
                    <span style={{fontFamily:mono, fontWeight:600, minWidth:"60px"}}>{label}</span>
                    <span style={{fontSize:"10px", color:c.textTer}}>{seat.wave.toUpperCase()} · {seat.tier}</span>
                    <span style={{fontSize:"10px", fontFamily:mono, color:statusColor(seat.status)}}>{seat.status}</span>
                    {seat.owner && <span style={{fontSize:"10px", color:c.textSec}}>{seat.owner}</span>}
                    {seat.lastSalePrice && <span style={{fontSize:"10px", fontFamily:mono}}>{fmt(seat.lastSalePrice)}</span>}
                  </div>
                  <div>
                    {seat.status === "AVAILABLE" && <button style={base.adminBtn(c.green)} onClick={() => { setAdminEditing(seat.id); setTransferSeatId(null); }}>Record Sale</button>}
                    {seat.status === "TAKEN" && <button style={base.adminBtn(c.blue)} onClick={() => { setTransferSeatId(seat.id); setAdminEditing(null); }}>Record Transfer</button>}
                    {seat.status === "TAKEN" && <button style={base.adminBtn()} onClick={() => { setAdminEditing(seat.id); setTransferSeatId(null); }}>Edit</button>}
                  </div>
                </div>
                {isEditing && seat.status === "AVAILABLE" && (
                  <div style={base.adminForm}>
                    <div style={base.adminFormRow}>
                      <div style={{flex:1, minWidth:"120px"}}><label style={base.label}>Owner Name</label><input style={base.input} value={adminForm.owner||""} onChange={e=>setAdminForm({...adminForm,owner:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"120px"}}><label style={base.label}>Entity</label><input style={base.input} value={adminForm.entity||""} onChange={e=>setAdminForm({...adminForm,entity:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"100px"}}><label style={base.label}>Sale Price</label><input style={base.input} type="number" value={adminForm.price||""} onChange={e=>setAdminForm({...adminForm,price:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"130px"}}><label style={base.label}>Signal</label>
                        <select style={base.select} value={adminForm.signal||""} onChange={e=>setAdminForm({...adminForm,signal:e.target.value})}>
                          <option value="ACCEPTING_INQUIRIES">Accepting Inquiries</option>
                          <option value="NOT_ACCEPTING">Not Accepting</option>
                          <option value="UNLISTED">Unlisted</option>
                        </select>
                      </div>
                      <div style={{display:"flex", gap:"6px", paddingBottom:"1px"}}>
                        <button style={base.adminBtn(c.green)} onClick={() => recordSale(seat.id)}>Confirm Sale</button>
                        <button style={base.adminBtn()} onClick={() => setAdminEditing(null)}>Cancel</button>
                      </div>
                    </div>
                  </div>
                )}
                {isEditing && seat.status === "TAKEN" && (
                  <div style={base.adminForm}>
                    <div style={base.adminFormRow}>
                      <div style={{flex:1, minWidth:"120px"}}><label style={base.label}>Owner Name</label><input style={base.input} value={adminForm.owner||seat.owner||""} onChange={e=>setAdminForm({...adminForm,owner:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"120px"}}><label style={base.label}>Entity</label><input style={base.input} value={adminForm.entity||seat.ownerEntity||""} onChange={e=>setAdminForm({...adminForm,entity:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"130px"}}><label style={base.label}>Signal</label>
                        <select style={base.select} value={adminForm.signal||seat.signal||""} onChange={e=>setAdminForm({...adminForm,signal:e.target.value})}>
                          <option value="ACCEPTING_INQUIRIES">Accepting Inquiries</option>
                          <option value="NOT_ACCEPTING">Not Accepting</option>
                          <option value="UNLISTED">Unlisted</option>
                        </select>
                      </div>
                      <div style={{display:"flex", gap:"6px", paddingBottom:"1px"}}>
                        <button style={base.adminBtn(c.blue)} onClick={() => updateSeat(seat.id)}>Save</button>
                        <button style={base.adminBtn()} onClick={() => setAdminEditing(null)}>Cancel</button>
                      </div>
                    </div>
                  </div>
                )}
                {isTransfer && (
                  <div style={base.adminForm}>
                    <div style={base.adminFormRow}>
                      <div style={{flex:1, minWidth:"120px"}}><label style={base.label}>New Owner</label><input style={base.input} value={adminForm.owner||""} onChange={e=>setAdminForm({...adminForm,owner:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"120px"}}><label style={base.label}>New Entity</label><input style={base.input} value={adminForm.entity||""} onChange={e=>setAdminForm({...adminForm,entity:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"100px"}}><label style={base.label}>Transfer Price</label><input style={base.input} type="number" value={adminForm.price||""} onChange={e=>setAdminForm({...adminForm,price:e.target.value})} /></div>
                      <div style={{flex:1, minWidth:"130px"}}><label style={base.label}>Signal</label>
                        <select style={base.select} value={adminForm.signal||""} onChange={e=>setAdminForm({...adminForm,signal:e.target.value})}>
                          <option value="ACCEPTING_INQUIRIES">Accepting Inquiries</option>
                          <option value="NOT_ACCEPTING">Not Accepting</option>
                          <option value="UNLISTED">Unlisted</option>
                        </select>
                      </div>
                      <div style={{display:"flex", gap:"6px", paddingBottom:"1px"}}>
                        <button style={base.adminBtn(c.blue)} onClick={() => recordTransfer(seat.id)}>Confirm Transfer</button>
                        <button style={base.adminBtn()} onClick={() => setTransferSeatId(null)}>Cancel</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <button style={{...base.adminBtn(), padding:"10px 20px", marginTop:"16px"}} onClick={() => {
          const data = JSON.stringify({seats, inquiries, exported:new Date().toISOString()}, null, 2);
          const blob = new Blob([data], {type:"application/json"});
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a"); a.href=url;
          a.download = `command-registry-${new Date().toISOString().split("T")[0]}.json`;
          a.click(); URL.revokeObjectURL(url);
          notify("Registry exported");
        }}>Export Snapshot</button>
      </div>
    );
  };

  // ═══════════════════════════════════════════
  // EXPLAINER
  // ═══════════════════════════════════════════

  const renderExplainer = () => (
    <div style={base.overlay} onClick={() => setShowExplainer(false)}>
      <div style={base.modal} onClick={e => e.stopPropagation()}>
        <div style={base.modalTitle}>How the COMMAND Seat Registry Works</div>
        <div style={{marginBottom:"20px"}}><div style={{fontWeight:600, marginBottom:"6px"}}>What is this?</div><p style={{color:c.textSec, margin:"0 0 8px", lineHeight:"1.7"}}>The COMMAND Seat Registry tracks 17 licensed positions for COMMAND · powered by MO§ES™. Each seat represents a permanent, transferable license. No additional seats will be created.</p></div>
        <div style={{marginBottom:"20px"}}><div style={{fontWeight:600, marginBottom:"6px"}}>Seat IDs</div><p style={{color:c.textSec, margin:"0", lineHeight:"1.7"}}>Each seat carries a Roman numeral ID prefixed with C — CI through CXVII. Transfer history is shown as a superscript: CI¹ has transferred once, CI² twice. The superscript is a permanent lineage depth indicator.</p></div>
        <div style={{marginBottom:"20px"}}><div style={{fontWeight:600, marginBottom:"6px"}}>Steps & Waves</div><p style={{color:c.textSec, margin:"0 0 8px", lineHeight:"1.7"}}>Seats are organized into four wave steps. Step 1 (CW1a) is open at launch. Each step unlocks when the previous step fills completely.</p><div style={{fontFamily:mono, fontSize:"11px", color:c.textSec, lineHeight:"2", padding:"8px 0"}}><div><span style={{color:c.green}}>Step 1 — CW1a</span> · 5 Internal seats · $65,000</div><div><span style={{color:c.blue}}>Step 2 — CW1b</span> · 3 Embedded seats · $130,000</div><div><span style={{color:c.amber}}>Step 3 — CW2a</span> · 5 Internal seats · $195,000</div><div><span style={{color:c.red}}>Step 4 — CW2b</span> · 3 Embedded seats · $260,000</div><div><span style={{color:c.purple}}>CW3</span> · 1 Bid seat · open bid</div></div></div>
        <div style={{marginBottom:"20px"}}><div style={{fontWeight:600, marginBottom:"6px"}}>Seat Transfers</div><p style={{color:c.textSec, margin:"0", lineHeight:"1.7"}}>Seats are transferable between parties and between products. All transfers are confirmed by Ello Cello LLC and recorded on the registry. Each transfer increments the superscript on the seat ID.</p></div>
        <div style={{marginBottom:"20px"}}><div style={{fontWeight:600, marginBottom:"6px"}}>Displayed Prices</div><p style={{color:c.textSec, margin:"0", lineHeight:"1.7"}}>The registry shows the last confirmed sale price — the most recent completed, paid, and confirmed transaction. No asking prices or estimates are displayed.</p></div>
        <button style={base.modalClose} onClick={() => setShowExplainer(false)}>Close</button>
      </div>
    </div>
  );

  // ═══════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════

  return (
    <div style={base.app}>
      <div style={base.header}>
        <div>
          <div style={base.logo}>Command</div>
          <div style={base.logosub}>Seat Registry · powered by MO§ES™</div>
        </div>
        <div style={base.nav}>
          <button style={base.navBtn(view==="board"||view==="detail"||view==="inquiry")} onClick={() => setView("board")}>Board</button>
          <button style={base.navBtn(view==="admin")} onClick={() => setView("admin")}>Admin</button>
          <button style={{...base.navBtn(false), minWidth:"36px", textAlign:"center"}} onClick={() => setShowExplainer(true)}>?</button>
        </div>
      </div>
      <div style={base.stats}>
        <span><span style={base.statLabel}>Seats</span><span style={base.statVal}>{filled}/17</span></span>
        <span><span style={base.statLabel}>Revenue</span><span style={base.statVal}>{fmt(revenue)}</span></span>
        <span><span style={base.statLabel}>Active Wave</span><span style={{...base.statVal, color:WAVES.find(w=>w.key===activeWave)?.accent}}>CW{activeWave.toUpperCase()}</span></span>
      </div>
      {view==="board" && renderBoard()}
      {view==="detail" && renderDetail()}
      {view==="inquiry" && renderInquiry()}
      {view==="admin" && renderAdmin()}
      {showExplainer && renderExplainer()}
      {toast && <div style={base.toast}>{toast}</div>}
      <div style={base.footer}>COMMAND · powered by MO§ES™ · © 2026 Ello Cello LLC · All Rights Reserved</div>
    </div>
  );
}
