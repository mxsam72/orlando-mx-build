#!/usr/bin/env python3
"""Complete v009 source, QA, scenery and native build pipeline."""
from pathlib import Path
import sys,subprocess,argparse,os
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-only',action='store_true');a=p.parse_args()
 env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
 scripts=['materialize_v009_baseline.py','analyze_v009_sections.py','rebuild_v009_geometry.py','qa_v009_geometry.py','render_v009_sections.py','rebind_v009_scenery.py','prepare_v009_release.py']
 if not a.source_only:scripts.append('build_windows_v009.py')
 for i,name in enumerate(scripts,1):
  print(f'[{i}/{len(scripts)}] {name}',flush=True);subprocess.run([sys.executable,str(R/'TOOLS'/name)],cwd=R,env=env,check=True)
 print('SOURCE QA COMPLETE' if a.source_only else 'V009 PKZ COMPLETE',flush=True)
if __name__=='__main__':main()
