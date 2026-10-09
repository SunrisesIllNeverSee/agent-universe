"""SIGNOMY read-only source observations and deterministic planning artifacts.

No writes outside this workflow folder. No production operations, network calls,
Git mutations, external agent calls, or phase approvals. The controller is the
only process allowed to award task PASS receipts.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def canonical(data):
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def settings():
    s = read_json(BASE / 'settings.json')
    runtime = Path(os.environ.get('SIGNOMY_RUNTIME_REPO',s['runtime_repo'])).expanduser().resolve()
    archive = Path(os.environ.get('SIGNOMY_DESIGN_ARCHIVE',s['design_archive'])).expanduser().resolve()
    return s, runtime, archive


def required(path, info):
    if not path.is_file():
        raise RuntimeError(f'{info} missing: {path}')
    return path


def git(repo, *args):
    if not repo.is_dir():
        raise RuntimeError(f'Runtime checkout not found: {repo}')
    p = subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(f'git {" ".join(args)} failed in {repo}: {p.stderr.strip()}')
    return p.stdout.strip()


def verify_commit(repo, prefix):
    actual = git(repo,'rev-parse','--verify',f'{prefix}^{{commit}}')
    if not actual.startswith(prefix):
        raise RuntimeError(f'Incorrect git commit identity for {prefix}')
    p = subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',actual,'HEAD'],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(f'Required landed commit {prefix} is not an ancestor of active runtime HEAD')
    return actual


def get_t0():
    s,r,a = settings()
    closeout=required(a/'reports/phase-1/PHASE-1-CLOSEOUT.md','Phase 1 closeout')
    if 'PHASE 1 FROZEN' not in closeout.read_text(encoding='utf-8'):
        raise RuntimeError('No Phase 1 frozen closeout verdict')
    spec={}
    for name in s['frozen_contracts']:
        file=required(a/'reports/phase-1'/name,'Frozen contract')
        if 'status: PHASE-1 FROZEN (2026-10-07)' not in file.read_text(encoding='utf-8'):
            raise RuntimeError(f'Not marked frozen: {name}')
        spec[name]=sha(file)
    ptr=required(r/'docs/control-surface-design.md','Runtime contract pointer')
    xwalk=required(r/'docs/contracts/FROZEN-CONTRACT-IMPLEMENTATION-CROSSWALK.md','Corrected runtime crosswalk')
    pointer_txt=ptr.read_text(encoding='utf-8')
    for name in s['frozen_contracts']:
        if name not in pointer_txt:
            raise RuntimeError(f'Runtime pointer fails to name {name}')
    crosswalk_text=xwalk.read_text(encoding='utf-8')
    if not any(x in crosswalk_text for x in ('10-class registry', '10 named classes', '10 named Agreement')):
        raise RuntimeError('Crosswalk may not include the 10-class correction')
    must=['T0_FROZEN_POINTER','T0_CONTRACT_RUNTIME_MATRIX','T0_MATRIX_CORRECTIONS']
    commits={k:verify_commit(r,s['required_runtime_commits'][k]) for k in must}
    return {'status':'source_evidence_verified_not_T0_gate_passed','runtime_head':git(r,'rev-parse','HEAD'),
            'contracts_frozen':len(spec),'contract_sha256':spec,'closeout_sha256':sha(closeout),
            'runtime_crosswalk_sha256':sha(xwalk),'runtime_pointer_sha256':sha(ptr),
            'verified_ancestor_commits':commits,'external_repos':{'runtime':str(r),'design_archive':str(a)},
            'limitations':['No T0 deliberate mutation/red-green evidence verified here',
                           'Current source provenance does not constitute release or implementation approval']}


def get_h5():
    s,r,a=settings()
    commit=verify_commit(r,s['required_runtime_commits']['H5_PRIVACY_COMMS'])
    report=required(r/'H5-COMMS-GATE-REPORT.md','H5 gate report')
    review=required(r/'reviews/H5-Comms-Independent-Review.md','H5 independent review')
    findings=required(r/'reviews/H5-Comms-Findings.csv','H5 ledger')
    doc=report.read_text(encoding='utf-8')
    if '475/475' not in doc or 'PASS' not in doc:
        raise RuntimeError('H5 report does not substantiate expected declared claims')
    return {'source':'committed H5 report','commit':commit,'report_sha256':sha(report),
            'review_sha256':sha(review),'findings_sha256':sha(findings),
            'declared_result':'H5 safe communications subset PASS; 475/475 tests locally reported',
            'assurance':'reviewed source evidence; no test rerun by this adapter',
            'deliberate_holds':['agent inbox scoped realtime transport','mission-channel Agreement/WorkEntry ACL',
                               'forum-to-motion promotion','thread-close route']}


def get_vote():
    s,r,a=settings()
    commit=verify_commit(r,s['required_runtime_commits']['H1H3_GOVERNANCE_VOTE'])
    code=required(r/'app/mcp_bridge.py','MCP vote bridge')
    tests=required(r/'tests/test_h5_comms.py','vote parity test module')
    txt=code.read_text(encoding='utf-8')
    if 'vote_cast_mcp' not in txt or 'motion_resolved' not in txt:
        raise RuntimeError('MCP vote bridge lacks expected mutation/audit evidence')
    return {'source':'committed H1/H3 govern.vote correction','commit':commit,
            'bridge_sha256':sha(code),'tests_sha256':sha(tests),
            'declared_result':'MCP govern.vote authoritative-state correction, 478/478 tests locally reported',
            'assurance':'committed-source observation, not independent test rerun',
            'open_wart':'REST cast_vote lacks meeting-open guard; correct consistently across both transports',
            'h1h3_entire_lane_complete':False}


def get_inventory():
    s,r,a=settings()
    handoff=a/'source/SIGNOMY-CIVITAE-design-handoff'
    jam=required(handoff/'02-diagrams/canonical-figjam-board.jam','Original native FigJam board')
    gallery=required(handoff/'START-HERE.html','Original gallery')
    samples=['system-interaction-map','operational-spine','mission-lifecycle','shell-states','unified-control-grammar']
    diagram_hashes={}
    for k in samples:
        image=required(handoff/'02-diagrams'/f'{k}.png',k)
        vector=required(handoff/'02-diagrams'/f'{k}.pdf',k)
        diagram_hashes[k]={'png_sha256':sha(image),'pdf_sha256':sha(vector)}
    published=list((handoff/'01-magicpath').glob('*/offline-preview.html'))
    if len(published)<s['expected_original_magicpath_previews']:
        raise RuntimeError(f'Only {len(published)} of {s["expected_original_magicpath_previews"]} offline previews present')
    return {'standing':'historical high-fidelity design reference; provisional, not frozen Phase 2 architecture',
            'figjam_sha256':sha(jam),'gallery_sha256':sha(gallery),
            'five_original_diagrams':diagram_hashes,
            'offline_magicpath_preview_count':len(published),
            'offline_previews':{x.parent.name:sha(x) for x in sorted(published)},
            'notes':['Original density/composition, colors and visual grammar take precedence over simplified generated overlays',
                     'Editable source not recovered for original MagicPath concepts; compiled offline previews remain usable',
                     'No external Figma/MagicPath calls needed to inventory these assets']}


def get_deltas():
    inv=required(BASE/'out/p2-original-asset-inventory.json','P2 inventory')
    source=required(BASE/'inputs/visual_delta_register.json','Visual delta register')
    obj=read_json(source)
    if len(obj['items'])<6 or not all(x.get('update_required') for x in obj['items']):
        raise RuntimeError('Visual delta register missing architectural coverage')
    return {'source_sha256':sha(source),'baseline_inventory_sha256':sha(inv),**obj}


def get_shell():
    src=required(BASE/'inputs/shell_brief.json','Shell preparation spec')
    delta=required(BASE/'out/p2-visual-deltas.json','Visual delta output')
    data=read_json(src)
    if not data.get('context') or not data.get('minimum_evidence'):
        raise RuntimeError('Shell brief incomplete')
    return {'source_sha256':sha(src),'design_delta_sha256':sha(delta),**data}

STAGES={
    't0':('out/t0-source-binding.json',get_t0),
    'h5':('out/h5-evidence.json',get_h5),
    'vote':('out/vote-evidence.json',get_vote),
    'inventory':('out/p2-original-asset-inventory.json',get_inventory),
    'deltas':('out/p2-visual-deltas.json',get_deltas),
    'shell':('out/p3-shell-preparation.json',get_shell),
}


def produce(stage):
    target,generator=STAGES[stage]
    dst=BASE/target
    data=generator()
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(canonical(data),encoding='utf-8')
    print(f'SOURCE-BASED ARTIFACT: {target}')


def check(stage):
    target,generator=STAGES[stage]
    actual=required(BASE/target,'Produced artifact').read_text(encoding='utf-8')
    expected=canonical(generator())
    if actual != expected:
        raise RuntimeError(f'{stage}: output does not match actual source evidence or frozen inputs')
    print('CHECK PASS: '+target)


def observe():
    """Create a fresh untrusted status projection; never change task state or receipts."""
    s,r,a=settings()
    tasks_file=BASE/'.roadmap/state.json'
    states={}
    if tasks_file.is_file():
        states={k:v['status'] for k,v in read_json(tasks_file).get('tasks',{}).items()}
    observed={}
    for name,fn in [('t0',get_t0),('h5',get_h5),('vote',get_vote),('p2',get_inventory)]:
        try:
            val=fn()
            observed[name]={'available':True,'evidence':val}
        except (RuntimeError,OSError,ValueError,KeyError) as err:
            observed[name]={'available':False,'reason':str(err)}
    out={'observed_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
         'type':'read_only_projection_not_a_controller_completion_receipt',
         'roadmap_task_statuses':states,'sources':observed,
         'guardrail':'A Git commit or file existing is not a passed implementation, independently verified gate, deployed state or owner approval.'}
    tracking=BASE/'tracking'
    tracking.mkdir(exist_ok=True)
    (tracking/'OBSERVED_STATUS.json').write_text(canonical(out),encoding='utf-8')
    lines=['# SIGNOMY — Fresh Source Observation','',f"Observed: {out['observed_at']}",'',
           'Read-only. Does not mark roadmap tasks passed or authorize implementation.','',
           '| Evidence source | Available | Detail |','|---|---|---|']
    for key,v in observed.items():
        detail='verified source evidence' if v['available'] else v.get('reason','missing').replace('|','/')
        lines.append(f'| {key} | {"yes" if v["available"] else "no"} | {detail} |')
    lines.extend(['','Controller task status comes only from receipts/attestations.',
                  'Refresh with `python3 steps/signomy.py observe` after each external change.'])
    (tracking/'OBSERVED_STATUS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Observed sources refreshed. NO task status changes. tracking/OBSERVED_STATUS.md')


def main():
    try:
        if len(sys.argv)==2 and sys.argv[1]=='observe':
            observe()
        elif len(sys.argv)==3 and sys.argv[1] in {'produce','check'} and sys.argv[2] in STAGES:
            (produce if sys.argv[1]=='produce' else check)(sys.argv[2])
        else:
            raise RuntimeError('Usage: signomy.py {produce|check} {t0|h5|vote|inventory|deltas|shell} OR signomy.py observe')
    except (RuntimeError,OSError,ValueError,KeyError) as exc:
        print('SIGNOMY EVIDENCE ERROR:',exc,file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    sys.exit(main())
