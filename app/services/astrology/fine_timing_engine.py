"""Phase 3 deterministic fine timing engine."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.kp_engine import KPEngine
from app.services.astrology.event_signatures import EVENT_SIGNATURES

WEIGHTS={1:8.0,2:12.0,3:18.0,4:14.0,5:9.0}

@dataclass
class FineTimingWindow:
    start_date:str
    end_date:str
    score:float
    strength:str
    peak_date:str
    active_chain:List[str]

class FineTimingEngine:
    def __init__(self):
        self.dasha=DashaEngine(); self.gochar=GocharEngine(); self.kp=KPEngine()

    def _dt(self,s):
        x=datetime.fromisoformat(s.replace("Z","+00:00"))
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)

    async def rank_windows(self,canonical,vedic,event,start_dt,end_dt,limit=5):
        sig=EVENT_SIGNATURES.get(event,EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])
        moon=next(p for p in canonical.planets if p.body=="Moon").sidereal_longitude
        birth=self._dt(canonical.birth.utc_instant)
        kp=self.kp.calculate_kp(canonical)
        pmap={p.planet:set(p.all_signified_houses) for p in kp.planet_significators}
        periods=self.dasha.get_periods_in_range(moon,birth,start_dt,end_dt,max_level=3)
        out=[]
        for lord,ps,pe,lvl,parents in [x for x in periods if x[3]==3]:
            ws,we=max(ps,start_dt),min(pe,end_dt)
            if ws>=we: continue
            mid=ws+(we-ws)/2
            chain=self.dasha.get_dasha_at(moon,birth,mid)
            score=30.0
            for x in chain:
                hs=pmap.get(x.lord,set()); w=WEIGHTS.get(x.level,5)
                if hs.intersection(sig.primary_houses): score+=w
                elif hs.intersection(sig.supporting_houses): score+=w*.4
                if hs.intersection(sig.unfavorable_houses): score-=w*.55
            av=getattr(vedic,"ashtakavarga",None)
            if av:
                vals=[av.sarvashtakavarga_by_house.get(str(h),0) for h in (sig.ashtakavarga_houses or sig.primary_houses)]
                if vals:
                    avg=sum(vals)/len(vals)
                    score += 7 if avg>=30 else (4 if avg>=25 else (-5 if avg<22 else 0))
            try:
                go=self.gochar.calculate_gochar_snapshot(canonical,mid)
                for t in go.transits:
                    if t.body in {"Jupiter","Saturn","Rahu","Ketu"}:
                        if t.house_from_d1_lagna in sig.primary_houses or t.house_from_moon in sig.primary_houses: score+=4
                        if t.house_from_d1_lagna in sig.unfavorable_houses: score-=2
            except Exception: pass
            # Sukshma/Pran locate an internal peak; do not imply day-level certainty.
            best_dt=mid; best=-1e9
            for i in range(9):
                dt=ws+(we-ws)*(i/8)
                ch=self.dasha.get_dasha_at(moon,birth,dt); s=0
                for x in ch:
                    hs=pmap.get(x.lord,set()); w=WEIGHTS.get(x.level,5)
                    if hs.intersection(sig.primary_houses): s+=w
                    elif hs.intersection(sig.supporting_houses): s+=w*.35
                    if hs.intersection(sig.unfavorable_houses): s-=w*.5
                if s>best: best=s; best_dt=dt
            score=max(5,min(95,score))
            strength="VERY_HIGH" if score>=82 else ("HIGH" if score>=68 else ("MODERATE" if score>=54 else "LOW"))
            out.append(FineTimingWindow(ws.strftime("%Y-%m-%d"),we.strftime("%Y-%m-%d"),round(score,1),strength,best_dt.strftime("%Y-%m-%d"),[x.lord for x in chain]))
        return sorted(out,key=lambda x:x.score,reverse=True)[:limit]
