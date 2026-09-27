#!/usr/bin/env python3
"""Render the evidence-grounded correspondence; never synchronize by speed."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
def main():
 data=json.loads((R/'V009_SOURCE/section_station_map.json').read_text(encoding='utf-8'));q=np.load(R/'V009_SOURCE/baseline_route.npz')['q'];L=q[-1,3]
 out=R/'DOCUMENTATION/v009_qa';out.mkdir(exist_ok=True)
 fig,ax=plt.subplots(figsize=(10,12),layout='constrained');colors=plt.get_cmap('tab20')
 lines=['# v009 section-to-station mapping','',data['evidence_correction'],'','All stations below are existing construction coordinates, not surveyed distances. Boundaries carry 15-25 m uncertainty. The game anchors are search windows; G at 95 s points later than the actual signature face.', '', '| Section | Real seconds | Native station m | Confidence | Evidence |','|---|---:|---:|---|---|']
 for i,s in enumerate(data['sections']):
  a,b=s['route_station_start_m'],s['route_station_end_m'];label=s['section_id'];alias=s.get('physical_alias_of')
  lines.append(f"| {label} | {s['real_video_start_s']}-{s['real_video_end_s']} | {a:.0f} → {b:.0f}{' (wrap)' if a>b else ''} | {s['confidence']} | {s['landmark_basis']} |")
  if alias:continue
  mask=((q[:,3]-a)%L)<=((b-a)%L);ax.plot(q[mask,0],q[mask,1],'.',ms=2,color=colors(i))
  m=(a+(b-a)%L*.48)%L;x,z=[np.interp(m,q[:,3],q[:,k]) for k in [0,1]]
  ax.text(x+3,z+2,label+(' / S12' if label=='S01' else ''),fontsize=9,fontweight='bold',bbox=dict(facecolor='white',alpha=.8,edgecolor='none',pad=1))
 for st in np.arange(30,L,100):
  x,z,h=[np.interp(st,q[:,3],q[:,k]) for k in range(3)];ax.arrow(x,z,3*np.cos(h),3*np.sin(h),head_width=1.7,color='#303030')
 ax.set_aspect('equal');ax.set_xlabel('Game X (m)');ax.set_ylabel('Game Z (m)');ax.grid(alpha=.15)
 ax.set_title('v009 construction map — S01–S14\nS12 = S01; S13 overlaps S02/S03; S14 overlaps S03/S04',fontsize=13)
 fig.savefig(out/'section_plan.png',dpi=150);plt.close(fig)
 lines+=['','No distinct sector is invented for repeated footage. S14 leads onward through S04-S11 before returning to S01. The native loop remains closed.','', '## Video inspection notes','', '- Real 94.7 s: long dominant jump face after right berm; assign to J10b sector, not game 95 s merely because numbers match.','- Real ~74 s: substantial ramp with vegetation close on rider right; J08b sector.','- Real ~6/130 s and ~10/134 s: repeated left turn / utility-pole and ramp sequence.','- Real 156-160 s: end-screen footage; no terrain inference from these frames.','- Game minimap and pole positions used for station identification. No metric photogrammetry, camera calibration, or surveyed heights are claimed.']
 (R/'DOCUMENTATION/v009_section_station_map.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
 print('Mapped 14 reference windows to 11 physical sectors, with repeated footage explicitly aliased.')
if __name__=='__main__':main()
