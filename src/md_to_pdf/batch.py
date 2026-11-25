"""Deterministic input discovery and non-destructive output planning."""
from pathlib import Path

EXTENSIONS = {".md", ".markdown", ".mdown"}


def collect_sources(inputs, *, recursive=False):
    seen = set()
    sources = []
    for raw in inputs:
        path = Path(raw).resolve()
        if path.is_dir():
            candidates = sorted(path.rglob("*") if recursive else path.glob("*"))
        elif path.is_file() and path.suffix.lower() in EXTENSIONS:
            candidates = [path]
        else:
            raise ValueError(f"Not a Markdown file or folder: {path}")
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in EXTENSIONS:
                candidate = candidate.resolve()
                if candidate not in seen:
                    seen.add(candidate)
                    sources.append(candidate)
    if not sources:
        raise ValueError("No Markdown files found")
    return sources


def plan_outputs(sources, *, output_dir=None, explicit=None, html_only=False, overwrite=False):
    ext = ".html" if html_only else ".pdf"
    if explicit and (len(sources) != 1 or output_dir):
        raise ValueError("Explicit output requires a single source")
    jobs, used = [], set()
    protected = {p.resolve() for p in sources}
    for source in sources:
        target = (Path(explicit) if explicit else
                  Path(output_dir) / (source.stem + ext) if output_dir else
                  source.with_suffix(ext)).resolve()
        if target in protected or target in used:
            raise ValueError(f"Output collision: {target}. Choose distinct names or convert next to sources.")
        if target.exists() and (not overwrite or not target.is_file()):
            raise ValueError(f"Output exists: {target}. Use overwrite to replace a file.")
        jobs.append((source, target))
        used.add(target)
    return jobs
