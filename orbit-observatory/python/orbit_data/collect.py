"""Small explicit-manifest collector. Does not write website data or scores."""

import argparse
import io
import json
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from . import VERSION
from .text import NORMALIZATION_VERSION, PageText, candidate_spans, html_text, normalize
from .validation import ROOT, digest, load_config, validate_dataset, validate_manifest

USER_AGENT = "ORBIT-Pilot/1.0 (bounded academic evidence collection)"


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class AllowedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https" or urlsplit(newurl).hostname not in self.hosts:
            raise ValueError("Redirect destination outside approved HTTPS hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Downloader:
    def __init__(self, output, hosts, retry_failures=False, refresh=False, interval=1.0, accept_header="text/html,application/pdf,text/plain"):
        self.output = output
        self.hosts = hosts
        self.retry_failures = retry_failures
        self.refresh = refresh
        self.interval = interval
        self.accept_header = accept_header
        self.last_request = {}
        self.opener = urllib.request.build_opener(AllowedRedirect(hosts))

    def fetch(self, url):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in self.hosts or parts.username or parts.password:
            raise ValueError("Only approved official HTTPS destinations are allowed")
        key = digest(url.encode())
        meta_path = self.output / "cache" / (key + ".json")
        if meta_path.exists() and not self.refresh:
            meta = json.loads(meta_path.read_text())
            if meta["status"] == "ok":
                raw = (self.output / meta["raw_path"]).read_bytes()
                if digest(raw) != meta["raw_sha256"]:
                    raise ValueError("Cached download checksum mismatch; refusing to use it")
                return raw, meta
            if not self.retry_failures:
                raise ValueError("Cached request failure: " + meta["error"])
        wait = self.interval - (time.monotonic() - self.last_request.get(parts.hostname, 0))
        if wait > 0:
            time.sleep(wait)
        self.last_request[parts.hostname] = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": self.accept_header})
            with self.opener.open(req, timeout=25) as response:
                raw = response.read(20_000_001)
                if len(raw) > 20_000_000:
                    raise ValueError("Download exceeds the 20 MB pilot limit")
                mime = response.headers.get_content_type()
                meta = dict(status="ok", requested_url=url, resolved_url=response.url,
                            retrieved_at=utcnow(), content_type=mime, raw_sha256=digest(raw))
            relative = "raw/" + meta["raw_sha256"] + ".bin"
            path = self.output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            meta["raw_path"] = relative
            write_json(meta_path, meta)
            return raw, meta
        except (urllib.error.URLError, OSError, ValueError) as error:
            write_json(meta_path, dict(status="error", requested_url=url, attempted_at=utcnow(),
                                       http_status=getattr(error, "code", None), error=str(error)))
            raise

    def check_robots(self, url):
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        try:
            raw, meta = self.fetch(robots_url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return
            raise
        except ValueError as e:
            # A cached 404 is the same policy result as the original response.
            cached = self.output / "cache" / (digest(robots_url.encode()) + ".json")
            meta = json.loads(cached.read_text()) if cached.exists() else {}
            if meta.get("http_status") == 404:
                return
            raise e
        if meta["content_type"] != "text/plain":
            raise ValueError("robots.txt did not return plain text; manual access review required")
        robot = urllib.robotparser.RobotFileParser()
        robot.parse(raw.decode("utf-8", errors="strict").splitlines())
        if not robot.can_fetch(USER_AGENT, url):
            raise ValueError("robots.txt disallows this request")
        delay = robot.crawl_delay(USER_AGENT) or robot.crawl_delay("*")
        if delay:
            self.interval = max(self.interval, float(delay))

    def download(self, url):
        self.check_robots(url)
        return self.fetch(url)


def extract(entry, downloader):
    raw, meta = downloader.download(entry["url"])
    extraction = entry["extraction"]
    canonical = meta["resolved_url"]
    if extraction["kind"] == "un_statement_pdf":
        if meta["content_type"] not in ("text/html", "application/xhtml+xml"):
            raise ValueError("Expected an official UN speech landing page")
        parser = PageText()
        parser.feed(raw.decode("utf-8", errors="strict"))
        actors, _ = load_config()
        expected_actor = actors[entry["actor_id"]]["name"]
        if "Statement\n" + expected_actor not in normalize("".join(parser.parts)):
            raise ValueError("UN landing page actor heading does not match the manifest")
        language = entry["language"]
        language_names = {"en": "english", "fr": "french"}
        links = {urljoin(meta["resolved_url"], href) for href, lang, title in parser.links
                 if urlsplit(urljoin(meta["resolved_url"], href)).hostname in {"gadebate.un.org", "gadebatestatements.un.org"}
                 and urlsplit(href).path.lower().endswith(".pdf")
                 and (lang == language or language_names.get(language, language) in title.lower()
                      or re.search(r"[_/-]" + re.escape(language) + r"\.pdf(?:\?|$)", href, re.I))}
        if len(links) != 1:
            raise ValueError(f"Expected one official {language} statement PDF; found {len(links)}. Review the manifest, do not substitute a UN summary.")
        raw, meta = downloader.download(links.pop())
        if not raw.startswith(b"%PDF-"):
            raise ValueError("Statement attachment is not a PDF")
        reader = PdfReader(io.BytesIO(raw))
        text = normalize("\n".join(page.extract_text() or "" for page in reader.pages))
    elif extraction["kind"] == "html":
        if meta["content_type"] not in ("text/html", "application/xhtml+xml"):
            raise ValueError("Expected HTML source")
        text, parser = html_text(raw, extraction)
        if parser.canonical:
            canonical = urljoin(meta["resolved_url"], parser.canonical)
    else:
        raise ValueError("Unsupported extraction kind")
    if len(text) < 200:
        raise ValueError("Extracted text too short; may be a challenge/error page")
    for alternatives in entry["identity_markers"]:
        if not any(marker.casefold() in text.casefold() for marker in alternatives):
            raise ValueError("Required source identity marker missing: " + repr(alternatives))
    return text, meta, canonical


def build_records(manifest, output, downloader):
    entries = validate_manifest(manifest)
    _, lenses = load_config()
    documents, outcomes = [], []
    for entry in entries.values():
        try:
            text, meta, canonical = extract(entry, downloader)
            text_hash = digest(text.encode("utf-8"))
            text_path = "text/" + text_hash + ".txt"
            (output / "text").mkdir(parents=True, exist_ok=True)
            (output / text_path).write_bytes(text.encode("utf-8"))
            document = dict(schema_version="1.0.0", record_type="document", id=entry["id"],
                            actor_id=entry["actor_id"], event_id=entry["event_id"], title=entry["title"],
                            issuer=entry["issuer"], publisher=entry["publisher"], canonical_url=canonical,
                            manifest_url=entry["url"], resolved_url=meta["resolved_url"],
                            delivery_date=entry["delivery_date"], publication_date=entry["publication_date"],
                            date_basis=entry["date_basis"], retrieved_at=meta["retrieved_at"], language=entry["language"],
                            source_scope_version="official-scope-v1", stream=entry["stream"],
                            raw_sha256=meta["raw_sha256"], text_sha256=text_hash,
                            normalization_version=NORMALIZATION_VERSION, raw_path=meta["raw_path"], text_path=text_path,
                            duplicate_of=entry["duplicate_of"], translation_of=entry["translation_of"],
                            translation_provenance=entry["translation_provenance"],
                            rights_status="local_research_only_not_cleared_for_redistribution")
            documents.append(document)
            outcomes.append(dict(id=entry["id"], actor_id=entry["actor_id"], url=entry["url"], status="collected", error=None))
        except (urllib.error.URLError, OSError, ValueError, UnicodeError, PyPdfError) as error:
            outcomes.append(dict(id=entry["id"], actor_id=entry["actor_id"], url=entry["url"], status="blocked", error=str(error)))

    records = list(documents)
    ids = {d["id"] for d in documents}
    # Do not emit dangling translation/copy relations if their target failed.
    for doc in documents:
        for key in ("duplicate_of", "translation_of"):
            if doc[key] and doc[key] not in ids:
                raise ValueError(f"{doc['id']} references an unavailable {key}; fix collection before publishing records")
    by_event = {}
    for doc in documents:
        by_event.setdefault(doc["event_id"], []).append(doc)
    for event_id, docs in sorted(by_event.items()):
        entry = entries[docs[0]["id"]]
        # Exact text copies only deduplicate within a declared communication event.
        # A later new act of communication may legitimately repeat its wording.
        seen = {}
        for doc in sorted(docs, key=lambda d: (bool(d["duplicate_of"] or d["translation_of"]), d["id"])):
            key = (doc["actor_id"], doc["language"], doc["text_sha256"])
            if key in seen and not doc["translation_of"] and not doc["duplicate_of"]:
                doc["duplicate_of"] = seen[key]
            else:
                seen[key] = doc["id"]
        records.append(dict(schema_version="1.0.0", record_type="event", id=event_id,
                            actor_ids=sorted({d["actor_id"] for d in docs}), event_date=entry["event_date"],
                            event_type="official_statement", source_scope_version="official-scope-v1",
                            stream=entry["stream"], document_ids=sorted(d["id"] for d in docs),
                            duplicate_cluster_id=event_id, joint_statement_id=None,
                            clustering_method="manifest_review_required"))
        for doc in docs:
            if doc["duplicate_of"] or doc["translation_of"]:
                continue
            text = (output / doc["text_path"]).read_text(encoding="utf-8")
            for lens in lenses.values():
                if entry["event_date"] < lens["applicable_from"] or (lens["applicable_until"] and entry["event_date"] > lens["applicable_until"]):
                    continue
                keywords = lens.get("candidate_keywords_by_language", {"en": lens["candidate_keywords"]}).get(doc["language"], [])
                for start, end, quote in candidate_spans(text, keywords):
                    identifier = f"{doc['id']}:{doc['text_sha256']}:{lens['id']}:{start}:{end}"
                    records.append(dict(schema_version="1.0.0", record_type="claim", id="claim-" + digest(identifier.encode()),
                                        document_id=doc["id"], event_id=event_id, lens_id=lens["id"], target_text=lens["definition"],
                                        start=start, end=end, quote=quote, text_sha256=doc["text_sha256"],
                                        offset_unit="unicode_code_point_half_open", speaker=None, attribution_status="pending",
                                        status="annotation_candidate", selection_method="keyword_paragraph_v1",
                                        qualifications=None, unresolved_reason="Paragraph candidate; speaker, scope, stance and atomic claim boundaries await human review."))
    records.sort(key=lambda r: (r["record_type"], r["id"]))
    validate_dataset(records, output)
    return records, outcomes


def collect(manifest_path, output, retry_failures=False, refresh=False, metadata_output=None):
    manifest = json.loads(manifest_path.read_text())
    actors, _ = load_config()
    output.mkdir(parents=True, exist_ok=True)
    downloader = Downloader(output, {h for a in actors.values() for h in a["official_hosts"]}, retry_failures, refresh)
    records, outcomes = build_records(manifest, output, downloader)
    # Rebuild, never append. Stable IDs and cached retrieval times yield identical reruns.
    write_json(output / "records.json", records)
    coverage = {}
    for actor in actors:
        targets = [o for o in outcomes if o["actor_id"] == actor]
        success_ids = {o["id"] for o in targets if o["status"] == "collected"}
        unique = [r for r in records if r["record_type"] == "document" and r["id"] in success_ids
                  and not r["duplicate_of"] and not r["translation_of"]]
        coverage[actor] = dict(target_documents=len(targets), collected_copies=len(success_ids), distinct_documents=len(unique))
    report = dict(schema_version="1.0.0", manifest_version=manifest["manifest_version"],
                  manifest_sha256=digest(manifest_path.read_bytes()), generated_at=utcnow(),
                  collector_version=VERSION,
                  contract_hashes={str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in
                                   (ROOT / "configs/v1/actors.json", ROOT / "configs/v1/lenses.json", ROOT / "schemas/v1/records.schema.json")},
                  normalization_version=NORMALIZATION_VERSION, coverage=coverage, outcomes=outcomes,
                  counts=dict(Counter(r["record_type"] for r in records)),
                  limitations=["Explicit pilot sample, not archive coverage or annual estimates.",
                               "Manifest dates and event grouping require source review; publication dates may be unknown.",
                               "Paragraph candidates are unannotated; no human labels, editorial scores or model predictions generated.",
                               "Local-only cache; redistribution rights and full site terms review remain pending."])
    write_json(output / "report.json", report)
    if metadata_output is not None:
        # No source text, candidate quotations, or downloaded bytes in this export.
        write_json(metadata_output / "collection.json", dict(report=report,
                   records_sha256=digest((output / "records.json").read_bytes()),
                   documents=[r for r in records if r["record_type"] == "document"]))
    print(json.dumps(dict(coverage=coverage, counts=report["counts"], output=str(output)), indent=2))
    return 0 if all(o["status"] == "collected" for o in outcomes) else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "source_manifest/v1/pilot.json")
    parser.add_argument("--output", type=Path, default=ROOT.parent / ".local/pilot-v1")
    parser.add_argument("--retry-failures", action="store_true", help="Retry cached failures after access/configuration changes")
    parser.add_argument("--refresh", action="store_true", help="Refetch sources; retain old content-addressed artifacts")
    parser.add_argument("--metadata-output", type=Path, help="Export provenance/coverage only, suitable for version control after review")
    args = parser.parse_args()
    raise SystemExit(collect(args.manifest, args.output, args.retry_failures, args.refresh, args.metadata_output))


if __name__ == "__main__":
    main()
