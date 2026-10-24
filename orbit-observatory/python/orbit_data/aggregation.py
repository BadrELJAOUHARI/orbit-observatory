"""Auditable claim/event/quarter weights. AI drafts can never enter this engine."""
import math
from collections import defaultdict
from datetime import date


def aggregate(rows, actor_id, lens_id, year, stream, *, allow_fixtures=False):
    eligible=[]
    event_dates={}
    for row in rows:
        if (row['actor_id'],row['lens_id'],row['stream'])!=(actor_id,lens_id,stream):
            raise ValueError('Aggregate must use one actor, lens and declared communication stream')
        day=date.fromisoformat(row['event_date'])
        if day.year!=year:raise ValueError('Evidence falls outside requested year')
        fixture=row.get('origin')=='test_fixture'
        if fixture and not allow_fixtures:raise ValueError('Fixture requires explicit opt-in')
        if not fixture and (row.get('origin')!='calibrated_model' or not row.get('eligibility_cleared')
            or not row.get('evaluation_approved') or not row.get('model_version') or not row.get('calibration_version')):
            raise ValueError('Only eligible, evaluated calibrated outputs can enter real scoring')
        p=row['support_probability']
        if isinstance(p,bool) or not isinstance(p,(float,int)) or not math.isfinite(p) or not 0<=p<=1:
            raise ValueError('Invalid support probability')
        if row['event_id'] in event_dates and event_dates[row['event_id']]!=day:
            raise ValueError('One event has conflicting dates')
        event_dates[row['event_id']]=day
        eligible.append((row,day,(day.month-1)//3+1,2*p-1))
    if eligible and len({r['origin'] for r,_,_,_ in eligible})!=1:
        raise ValueError('Cannot mix synthetic fixtures with real outputs')
    events=defaultdict(dict)
    duplicates=defaultdict(list)
    for row,day,q,score in eligible:
        # Explicit canonical claim identity must collapse repeats, mirrors and translations.
        k=row['canonical_claim_key']
        old=events[row['event_id']].get(k)
        if old and old[3]!=score:raise ValueError('Duplicate canonical claim has conflicting scores')
        events[row['event_id']].setdefault(k,(row,day,q,score))
        duplicates[(row['event_id'],k)].append(row['claim_id'])
    quarters=defaultdict(list)
    for event,claims in events.items():quarters[next(iter(claims.values()))[2]].append(event)
    Q=len(quarters)
    ledger=[]
    for event,claims in sorted(events.items()):
        q=next(iter(claims.values()))[2]
        weight=1/(Q*len(quarters[q]))
        for k,(row,day,_,score) in sorted(claims.items()):
            ledger.append(dict(actor_id=actor_id,lens_id=lens_id,year=year,stream=stream,event_id=event,
                event_date=day.isoformat(),quarter=q,canonical_claim_key=k,claim_id=row['claim_id'],
                duplicate_claim_ids=sorted(set(duplicates[(event,k)])),event_weight=weight,
                claims_in_event=len(claims),claim_weight=weight/len(claims),score=score,
                contribution=weight*score/len(claims),origin=row['origin']))
    counts={str(q):len(quarters[q]) for q in range(1,5)}
    dates={str(q):len({event_dates[e] for e in quarters[q]}) for q in range(1,5)}
    gate=all(counts[str(q)]>=2 and dates[str(q)]>=2 for q in range(1,5))
    window_score=sum(r['contribution'] for r in ledger) if ledger else None
    event_weights=[1/(Q*len(quarters[q])) for q in quarters for e in quarters[q]]
    return dict(aggregation_version='hierarchy-1.0.0',actor_id=actor_id,lens_id=lens_id,year=year,stream=stream,
        origin='test_fixture' if ledger and ledger[0]['origin']=='test_fixture' else 'calibrated_model' if ledger else 'no_eligible_evidence',
        covered_quarters=Q,events_by_quarter=counts,distinct_dates_by_quarter=dates,annual_coverage_gate_passed=gate,
        annual_score=window_score if gate else None,provisional_observed_window_score=window_score,
        effective_event_count=1/sum(w*w for w in event_weights) if event_weights else None,
        coverage_start=min(event_dates.values()).isoformat() if event_dates else None,
        coverage_end=max(event_dates.values()).isoformat() if event_dates else None,
        publishable=bool(gate and ledger and ledger[0]['origin']=='calibrated_model'),
        ledger=ledger,limitations='Coverage gate is provisional. Observed-window score is not an annual replacement. No unseen-source coverage or statistical precision is implied.')
