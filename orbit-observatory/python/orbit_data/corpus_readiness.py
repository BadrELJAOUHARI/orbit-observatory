"""Inventory distinct events separately from retrieval and independently reviewed labels."""
import csv,json
from collections import Counter,defaultdict
from .validation import ROOT,load_config,digest
from .expansion import OUT,PACKET
from .reviewed import write_immutable
from .workflow import write_csv
from .training import check_baseline_fixtures


def build():
    all_docs=json.loads((OUT/'cleared_catalog.json').read_text());docs=all_docs
    docs=[d for d in docs if not d['duplicate_of'] and d['event_identity_verified']]
    old=json.loads((ROOT.parent/'.local/pilot-v1/records.json').read_text())
    events={r['id']:r for r in old if r['record_type']=='event'}
    # Original event record type is event, with frozen event_date.
    inventory=[]
    for d in docs:inventory.append(dict(id=d['document_id'],event_id=d['event_id'],actor_id=d['actor_id'],year=int(d['event_date'][:4]),stream=d['selection_method'],held=bool(d['quality_issues'])))
    for d in old:
        if d['record_type']=='document':
            event=events[d['event_id']]
            inventory.append(dict(id=d['id'],event_id=d['event_id'],actor_id=d['actor_id'],year=int(event['event_date'][:4]),stream='pilot_purposive',held=True))
    originals=json.loads((ROOT.parent/'.local/workflow-v1/review_queue.json').read_text())
    returned={r['candidate_id']:r for r in json.loads((ROOT.parent/'.local/workflow-returns/Badr_A-development-0001/returned_rows.json').read_text())}
    from .workflow import load_corpus
    *_,historic_annotations,assessments,control_ids=load_corpus()
    observations=[]
    for r in originals:
        latest=returned.get(r['candidate_id'])
        label=latest['human_label'] if latest else historic_annotations.get(r['candidate_id'],{}).get('label','')
        observations.append(dict(actor_id=r['actor_id'],lens_id=r['lens_id'],year=int(r['event_date'][:4]),event_id=r['event_id'],document_id=r['document_id'],
            passage_id=r['passage_id'],label=label,held=r['quarantine']=='true' or bool(latest and latest['human_scope']=='partial_scope'),
            reviewed=bool(label),selection_kind=r['selection_kind']))
    by_doc={d['document_id']:d for d in docs}
    for c in json.loads((OUT/'candidates.json').read_text()):
        d=by_doc[c['document_id']]
        observations.append(dict(actor_id=d['actor_id'],lens_id=c['lens_id'],year=int(d['event_date'][:4]),event_id=c['event_id'],document_id=c['document_id'],
            passage_id=d['document_id']+':'+str(c['start'])+':'+str(c['end']),label='',held=bool(c['quality_issues']),reviewed=False,selection_kind=c['selection_kind']))
    rows=[]
    lenses=load_config()[1]
    for actor in sorted({d['actor_id'] for d in inventory}):
        for year in range(2012,2027):
            population=[d for d in inventory if d['actor_id']==actor and d['year']==year]
            for lens in lenses:
                matches=[r for r in observations if r['actor_id']==actor and r['year']==year and r['lens_id']==lens]
                rows.append(dict(actor_id=actor,lens_id=lens,year=year,lens_applicable_in_year=year>=int(lenses[lens]['applicable_from'][:4]),year_status='partial_current_year' if year==2026 else 'completed_year',documents_in_inventory=len(population),retained_document_records_including_excluded_copies=len(population)+sum(d['actor_id']==actor and d['year']==year and bool(d['duplicate_of']) for d in all_docs),excluded_wrong_date_copy_records=sum(d['actor_id']==actor and d['year']==year and bool(d['duplicate_of']) for d in all_docs),distinct_events_in_inventory=len({d['event_id'] for d in population}),
                    documents_with_candidates=len({r['document_id'] for r in matches}),candidate_events=len({r['event_id'] for r in matches}),
                    candidate_passage_lens_pairs=len(matches),candidate_passages=len({r['passage_id'] for r in matches}),
                    reviewed_relevant_claims=sum(r['label'] in ('support','oppose','mixed') for r in matches),
                    reviewed_relevant_claims_without_holds=sum(r['label'] in ('support','oppose','mixed') and not r['held'] for r in matches),
                    unresolved_reviewed_claims=sum(r['label']=='unresolved' for r in matches),source_or_evidence_held_pairs=sum(r['held'] for r in matches),
                    independent_human_labeled_events=0,approved_training_claims=0))
    write_immutable(OUT/'coverage.json',rows);write_csv(OUT/'coverage.csv',rows)
    reviewed=[r for r in observations if r['reviewed']]
    summary=dict(inventory_documents=len(inventory)+sum(bool(d['duplicate_of']) for d in all_docs),canonical_documents=len(inventory),excluded_wrong_date_copy_records=sum(bool(d['duplicate_of']) for d in all_docs),distinct_communication_events=len({d['event_id'] for d in inventory}),
        pilot_events=10,additional_focal_events=sum(d['actor_id'] in ('USA','EU','TUR','IND','ZAF') for d in inventory if d['stream']!='pilot_purposive'),
        auxiliary_events=sum(d['actor_id'] in ('RUS','UKR') for d in inventory),
        all_current_assisted_reviewed_labels=dict(Counter(r['label'] for r in reviewed)),
        current_reviewed_communication_events=len({r['event_id'] for r in reviewed}),
        approved_class_counts={label:0 for label in ('support','oppose','no_stance','mixed','unresolved')},
        independently_human_labeled_events=0,real_training_ready=False,
        coverage_definition='Inventory document/event counts repeat across lenses as denominators. Candidate passage-lens pairs are retrieval outputs, not established relevant claims. Reviewed relevant claims are reviewed support/oppose/mixed, including separately reported holds. Distinct events are not independent human judgments.',
        selection_bias='UN speeches are supplementary purposive September archive events. Targeted sources oversample policy language and are marked training acquisition; neither stream estimates representative annual country positions.',
        new_suggestions_generated=0,existing_AI_drafts_retained=True,evaluation_passages_exported_to_development=0)
    write_immutable(OUT/'corpus_inventory.json',summary)
    write_immutable(ROOT/'data/expansion-v6/corpus_inventory.json',summary)
    write_immutable(OUT/'baseline_fixture_check.json',check_baseline_fixtures())
    print(json.dumps(summary,indent=2))

if __name__=='__main__':build()
