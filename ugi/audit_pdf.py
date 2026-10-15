"""Explicit download/read-only PDF layout smoke; no OCR or semantic-F1 claim."""
import argparse
import json
import urllib.request
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .engine import Engine
from .models import Settings, now
from .store import Store

URL = "https://www.nasa.gov/wp-content/uploads/2016/01/armstrong_neil.pdf"


def run(path, download=False, backend="falkordb"):
    if download:
        with urllib.request.urlopen(URL, timeout=30) as response:
            data = response.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("Public PDF exceeds application upload quota")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    else:
        data = path.read_bytes()
    from pypdf import PdfReader

    reader = PdfReader(path)
    settings = Settings(backend=backend, provider="offline", graph_prefix="ugi_pdf_"+uuid4().hex[:12])
    store = Store(settings)
    try:
        report = Engine(store).ingest("armstrong.pdf", data)
        proofs = []
        for claim in store.claims() + store.events():
            ev = store.get(claim["evidence_id"])
            chunk = store.get(claim["chunk_id"])
            proofs.append(chunk["text"][ev["start"]:ev["end"]] == ev["quote"])
        return dict(recorded_at=now(), source_url=URL, source_sha256=sha256(data).hexdigest(),
                    licence="NASA-authored biography; US Government work, third-party media excluded",
                    licence_url="https://www.nasa.gov/nasa-brand-center/images-and-media/",
                    pages=len(reader.pages), backend=backend, ingestion=report,
                    exact_quotes=sum(proofs), emitted=len(proofs),
                    layout="Single page with photo, text wrapping, section headers and line breaks",
                    semantic_accuracy=None, ocr_supported=False,
                    limitations=["Extraction order/layout may break prose; exact quote does not prove entailment",
                                 "No exhaustive human labels for this PDF; no semantic F1",
                                 "Scanned-image, encrypted, >40-page and oversized PDFs unsupported"])
    finally:
        if store.client:
            assert store.graph.startswith(settings.graph_prefix+"_")
            store.client.execute_command("GRAPH.DELETE", store.graph)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--pdf", type=Path, default=Path(".evaluation-local/armstrong.pdf"))
    parser.add_argument("--backend", choices=["memory", "falkordb"], default="falkordb")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pdf, args.download, args.backend)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
