"""End-to-end synthetic check: no source repository is modified or deployed."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[2]


def put(file, text):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding='utf-8')


def call(argv, cwd=None):
    x = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if x.returncode:
        raise AssertionError(f'{argv}: {x.stdout}\n{x.stderr}')
    return x.stdout.strip()


class SignomyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.design=self.base/'design'
        self.repo=self.base/'runtime'
        self.workflow=self.base/'signomy'
        shutil.copytree(SRC/'workflows/signomy',self.workflow,ignore=shutil.ignore_patterns('tracking','out','.roadmap','ROADMAP_STATUS.md'))
        call(['git','init','-q',str(self.repo)])
        call(['git','-C',str(self.repo),'config','user.email','test@example.invalid'])
        call(['git','-C',str(self.repo),'config','user.name','Test'])
        s=json.loads((self.workflow/'settings.json').read_text())
        s['runtime_repo']=str(self.repo)
        s['design_archive']=str(self.design)
        c=self.design/'reports/phase-1'
        for name in s['frozen_contracts']:
            put(c/name,'---\nstatus: PHASE-1 FROZEN (2026-10-07)\n---\n')
        put(c/'PHASE-1-CLOSEOUT.md','PHASE 1 FROZEN — PHASE 2 DESIGN RE-BASELINE AUTHORIZED')
        put(self.repo/'docs/control-surface-design.md','\n'.join(s['frozen_contracts']))
        put(self.repo/'docs/contracts/FROZEN-CONTRACT-IMPLEMENTATION-CROSSWALK.md','10 named classes; O-IA-3 resolved; no completion percentage')
        put(self.repo/'H5-COMMS-GATE-REPORT.md','H5 PASS — 475/475 local tests')
        put(self.repo/'reviews/H5-Comms-Independent-Review.md','reverify PASS')
        put(self.repo/'reviews/H5-Comms-Findings.csv','status\nverified_fixed')
        put(self.repo/'app/mcp_bridge.py','vote_cast_mcp = True\nmotion_resolved = True')
        put(self.repo/'tests/test_h5_comms.py','def test_vote(): pass\ndef test_close_thread_owner_and_admin(): pass\ndef test_otel_span_no_unbound_metadata(): pass')
        put(self.repo/'app/routes/missions.py','"origin": "bounty"')
        put(self.repo/'app/routes/kassa.py','api/kassa/threads/{thread_id}/close\nstatus != "open"')
        put(self.repo/'app/seeds_otel.py','metadata = seed.get("metadata", {})\nmetadata.get("governance_mode")')
        design=self.design/'source/SIGNOMY-CIVITAE-design-handoff'
        put(design/'02-diagrams/canonical-figjam-board.jam','ARCHIVE')
        put(design/'START-HERE.html','gallery')
        for name in ['system-interaction-map','operational-spine','mission-lifecycle','shell-states','unified-control-grammar']:
            for ext in ['png','pdf']: put(design/'02-diagrams'/f'{name}.{ext}',f'{name} {ext}')
        for i in range(12):put(design/'01-magicpath'/f'concept-{i}'/'offline-preview.html','<h1>Offline</h1>')
        keys=['H5_PRIVACY_COMMS','T0_FROZEN_POINTER','T0_CONTRACT_RUNTIME_MATRIX','T0_MATRIX_CORRECTIONS','H1H3_GOVERNANCE_VOTE']
        for ix,k in enumerate(keys):
            put(self.repo/f'commit-{ix}.txt',k)
            call(['git','-C',str(self.repo),'add','.'])
            call(['git','-C',str(self.repo),'commit','-q','-m',k])
            s['required_runtime_commits'][k]=call(['git','-C',str(self.repo),'rev-parse','HEAD'])[:9]
        (self.workflow/'settings.json').write_text(json.dumps(s))

    def ctl(self,*args, success=True):
        p=subprocess.run([sys.executable,'-m','roadmap_engine','--project',str(self.workflow),*args],cwd=SRC,capture_output=True,text=True)
        if success:self.assertEqual(p.returncode,0,(p.stdout,p.stderr))
        else:self.assertNotEqual(p.returncode,0,(p.stdout,p.stderr))
        return p

    def test_source_observation_never_graduates_approval_and_detects_drift(self):
        self.ctl('validate')
        self.ctl('refresh')
        self.assertFalse((self.workflow/'.roadmap/state.json').exists())
        self.ctl('run')
        state=json.loads((self.workflow/'.roadmap/state.json').read_text())['tasks']
        passed={'T0_BIND','H5_RECORD','VOTE_RECORD','P2_INVENTORY','P2_DELTA','P3_SHELL_PREP','H2_ORPHAN_AUDIT','H5_CLOSE_RECORD','H3_OTEL_RECORD'}
        self.assertEqual({k for k,v in state.items() if v['status']=='passed'}, passed)
        self.assertEqual(state['T0_ADVERSARIAL']['status'],'blocked')
        self.assertEqual(state['P2_PROVISIONAL']['status'],'blocked')
        self.assertEqual(state['P3_AUTHORIZE']['status'],'pending')
        self.ctl('verify')
        assert (self.workflow/'ROADMAP_STATUS.md').is_file()
        self.ctl('refresh')
        observed=json.loads((self.workflow/'tracking/OBSERVED_STATUS.json').read_text())
        self.assertTrue(all(x['available'] for x in observed['sources'].values()))
        # An existing accepted artifact is immutable under the engine.
        (self.workflow/'out/p2-visual-deltas.json').write_text('{}')
        self.ctl('verify',success=False)

    def test_missing_original_source_fails_closed(self):
        x=self.design/'source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/canonical-figjam-board.jam'
        x.unlink()
        r=subprocess.run([sys.executable,str(self.workflow/'steps/signomy.py'),'produce','inventory'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('missing',r.stderr)

    def test_bad_frozen_contract_rejected(self):
        s=json.loads((self.workflow/'settings.json').read_text())
        file=self.design/'reports/phase-1'/s['frozen_contracts'][0]
        file.write_text('status: PRE-FREEZE')
        r=subprocess.run([sys.executable,str(self.workflow/'steps/signomy.py'),'produce','t0'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('Not marked frozen',r.stderr)

if __name__=='__main__':unittest.main()
