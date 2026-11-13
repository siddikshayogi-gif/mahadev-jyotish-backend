"""Phase-2 internal astrologer-style multi-layer prediction consensus engine."""
from dataclasses import dataclass, asdict
from typing import Any, Dict, List
from app.services.astrology.event_signatures import EVENT_SIGNATURES

@dataclass
class PredictionDecision:
    event: str; verdict: str; confidence: float
    natal_promise: str; varga_confirmation: str; kp_confirmation: str
    dasha_activation: str; transit_trigger: str
    ashtakavarga_support: str; shadbala_support: str
    confirmations: int; contradictions: int; internal_reasons: List[str]
    def to_dict(self)->Dict[str,Any]: return asdict(self)

class PredictionRuleEngine:
    def evaluate(self,event,vedic_chart,kp_chart,dasha_result,gochar_result,yoga_result):
        sig=EVENT_SIGNATURES.get(event,EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])
        pos=0.0; neg=0.0; conf=0; contra=0; reasons=[]
        lords=[h for h in vedic_chart.house_lordships if h.house_number in sig.primary_houses]
        good=sum(1 for h in lords if str(h.lord_dignity).split(".")[-1] not in {"DEBILITATED","ENEMY"})
        bad=len(lords)-good
        if good: pos+=min(18,good*6); conf+=1; reasons.append("Natal promise supports the event.")
        if bad: neg+=min(10,bad*4); contra+=1
        natal="PRESENT" if good>bad else ("MIXED" if good else "WEAK")

        vf=vedic_chart.vargas.get(sig.varga or "D1"); vh=0
        if vf and sig.varga!="D1":
            vh=sum(1 for p in sig.natural_significators if vf.planet_houses.get(p) in sig.primary_houses+sig.supporting_houses)
            if vh: pos+=min(14,vh*7); conf+=1; reasons.append("Relevant divisional chart confirms the natal promise.")
        varga="STRONG" if vh>=2 else ("PRESENT" if vh else "NEUTRAL")

        pmap={p.planet:set(p.all_signified_houses) for p in kp_chart.planet_significators}
        active=list(dasha_result.active_chain[:5]); kh=kb=0
        for p in active:
            hs=pmap.get(p.lord,set())
            if hs.intersection(sig.kp_event_houses or sig.primary_houses): kh+=1
            if hs.intersection(sig.unfavorable_houses): kb+=1
        if kh: pos+=min(18,kh*4.5); conf+=1; reasons.append("KP event-house linkage confirms the period.")
        if kb: neg+=min(10,kb*2.5); contra+=1
        kp="STRONG" if kh>=3 else ("PRESENT" if kh else "WEAK")

        weights=[8,7,6,4,3]; dh=0
        for i,p in enumerate(active):
            hs=pmap.get(p.lord,set())
            if hs.intersection(sig.primary_houses): pos+=weights[i]; dh+=1
            if hs.intersection(sig.unfavorable_houses): neg+=weights[i]*.55
        if dh: conf+=1; reasons.append("Active Vimshottari hierarchy activates the event.")
        dasha="STRONG" if dh>=3 else ("PRESENT" if dh else "WEAK")

        av="UNAVAILABLE"
        if getattr(vedic_chart,"ashtakavarga",None):
            vals=[vedic_chart.ashtakavarga.sarvashtakavarga_by_house.get(str(h),0) for h in (sig.ashtakavarga_houses or sig.primary_houses)]
            if vals:
                avg=sum(vals)/len(vals)
                if avg>=30: pos+=10; conf+=1; av="STRONG"
                elif avg>=25: pos+=6; conf+=1; av="SUPPORTIVE"
                elif avg<22: neg+=6; contra+=1; av="WEAK"
                else: av="NEUTRAL"

        sb="UNAVAILABLE"
        if getattr(vedic_chart,"shadbala",None):
            wanted=set(sig.shadbala_planets or sig.natural_significators)
            vals=[x.normalized_score for x in vedic_chart.shadbala.planets if x.planet in wanted]
            if vals:
                avg=sum(vals)/len(vals)
                if avg>=62: pos+=8; conf+=1; sb="STRONG"
                elif avg>=45: pos+=4; sb="SUPPORTIVE"
                elif avg<30: neg+=5; contra+=1; sb="WEAK"
                else: sb="NEUTRAL"

        th=tb=0
        for t in gochar_result.transits:
            if t.body not in set(sig.natural_significators)|{"Jupiter","Saturn","Rahu","Ketu"}: continue
            if t.house_from_d1_lagna in sig.primary_houses or t.house_from_moon in sig.primary_houses: th+=1
            if t.house_from_d1_lagna in sig.unfavorable_houses: tb+=1
        if th: pos+=min(12,th*4); conf+=1; reasons.append("Current transit supplies a timing trigger.")
        if tb: neg+=min(7,tb*2); contra+=1
        transit="STRONG" if th>=2 else ("PRESENT" if th else "NEUTRAL")

        pos+=min(4,sum(1 for y in yoga_result.yogas if y.is_active))
        score=max(5,min(95,42+pos-neg))
        minimum=sig.minimum_confirmations or 3
        if conf<minimum: score=min(score,64)
        if conf>=minimum+2 and score>=80: verdict="STRONGLY_SUPPORTED"
        elif conf>=minimum and score>=67: verdict="SUPPORTED"
        elif contra>conf or score<38: verdict="WEAK_OR_DELAYED"
        else: verdict="MIXED"
        return PredictionDecision(event,verdict,round(score,1),natal,varga,kp,dasha,transit,av,sb,conf,contra,reasons)
