"""Source merging for unb-consultant.

Plans and executes merging of small source files into composite documents
to stay within the NotebookLM source limit.
"""

import os
import re
import math
from pathlib import Path
from typing import NamedTuple

from unb_consultant.tier import get_source_limit, get_target_source_count, detect_tier, TIER_LIMITS
from unb_consultant.i18n import _


class MergeGroup(NamedTuple):
    """A group of files to be merged into one source document."""
    name: str
    files: list[Path]
    total_size: int
    keyword_score: float


class MergePlan(NamedTuple):
    """Full merge plan for a set of raw files."""
    groups: list[MergeGroup]
    raw_count: int
    merged_count: int
    target_count: int
    tier_limit: int
    skipped_large: int  # files > 50KB kept individual


# Stopwords for keyword extraction (English + Spanish)
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "can", "could",
    "shall", "should", "may", "might", "must", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her",
    "its", "our", "their", "me", "him", "us", "them",
    "and", "or", "but", "if", "because", "as", "until", "while", "of", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo",
    "al", "del", "de", "en", "por", "para", "con", "sin", "sobre",
    "entre", "tras", "durante", "mediante", "segun",
    "y", "e", "o", "u", "pero", "sino", "aunque",
    "que", "cual", "quien", "cuyo", "donde", "como", "cuando",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "aquel", "aquella", "aquellos", "aquellas",
    "mi", "tu", "su", "sus", "nuestro", "vuestro",
    "es", "son", "era", "fue", "ha", "han", "habia", "hubo",
    "sera", "seran", "sea", "sean", "sido",
    "tiene", "tienen", "tenia", "tuvo",
    "hace", "hacen", "hacia", "hizo",
    "muy", "mas", "menos", "tan", "tanto",
    "no", "si", "tambien", "ya", "aun", "nunca", "jamas",
    "todo", "toda", "todos", "todas", "cada", "varios", "ambos",
    "otro", "otra", "otros", "otras", "mismo", "misma", "propio",
    "se", "le", "les", "nos", "os", "me", "te",
}


def _extract_keywords(filepath: Path, max_lines: int = 5) -> set[str]:
    """Extract significant keywords from the first lines of a file."""
    keywords = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                # Remove markdown formatting
                text = re.sub(r"[#*_`\[\]()>|]", " ", line)
                text = re.sub(r"[{}]", " ", text)
                text = re.sub(r"[^a-zA-Z0-9\u00C0-\u024F\u00D1\u00F1\s]", " ", text)
                words = text.lower().split()
                for w in words:
                    w = w.strip()
                    if len(w) > 3 and w not in _STOPWORDS and not w.isdigit():
                        keywords.add(w)
    except (OSError, IOError):
        pass
    return keywords


def _keyword_affinity(kw1: set[str], kw2: set[str]) -> float:
    """Compute keyword affinity score between two sets (Jaccard-like)."""
    if not kw1 or not kw2:
        return 0.0
    intersection = kw1 & kw2
    union = kw1 | kw2
    if not union:
        return 0.0
    return len(intersection) / len(union)


def plan_merge(
    files: list[Path],
    target_count: int | None = None,
    tier_limit: int | None = None,
    large_file_threshold: int = 50 * 1024,  # 50KB
) -> MergePlan:
    """Plan source merging for a list of files.
    
    Args:
        files: List of file paths to merge.
        target_count: Desired number of output sources. Auto-calculated if None.
        tier_limit: Tier source limit. Auto-detected if None.
        large_file_threshold: Files above this size (bytes) are kept individual.

    Returns:
        MergePlan with groups and statistics.
    """
    if tier_limit is None:
        tier_limit = get_source_limit()
    if target_count is None:
        target_count = get_target_source_count()

    files = [f for f in files if f.is_file()]

    # Separate large and small files
    large_files = [f for f in files if f.stat().st_size >= large_file_threshold]
    small_files = [f for f in files if f.stat().st_size < large_file_threshold]

    # Large files stay individual
    large_groups = [
        MergeGroup(
            name=f.stem,
            files=[f],
            total_size=f.stat().st_size,
            keyword_score=1.0,
        )
        for f in sorted(large_files)
    ]

    # If small files fit within target, keep them individual too
    if len(small_files) <= (target_count - len(large_groups)):
        small_groups = [
            MergeGroup(
                name=f.stem,
                files=[f],
                total_size=f.stat().st_size,
                keyword_score=1.0,
            )
            for f in sorted(small_files)
        ]
        return MergePlan(
            groups=large_groups + small_groups,
            raw_count=len(files),
            merged_count=len(large_groups) + len(small_files),
            target_count=target_count,
            tier_limit=tier_limit,
            skipped_large=len(large_files),
        )

    # Need to merge small files
    # Extract keywords for each small file
    file_keywords = {f: _extract_keywords(f) for f in small_files}

    # Greedy clustering: start with each file as its own cluster
    # Then iteratively merge the pair with highest affinity
    class Cluster:
        def __init__(self, file: Path):
            self.files = [file]
            self.keywords = file_keywords[file]
            self.total_size = file.stat().st_size
            self.name = file.stem

        def affinity_with(self, other: "Cluster") -> float:
            return _keyword_affinity(self.keywords, other.keywords)

        def merge(self, other: "Cluster"):
            self.files.extend(other.files)
            self.keywords |= other.keywords
            self.total_size += other.total_size
            # Rename to reflect combined content
            self.name = f"{self.name}_{other.name}"
            if len(self.name) > 80:
                self.name = self.name[:80]

    clusters = [Cluster(f) for f in sorted(small_files)]

    max_clusters = target_count - len(large_groups)
    while len(clusters) > max_clusters and len(clusters) > 1:
        # Find pair with highest affinity
        best_score = -1.0
        best_pair = (0, 1)
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                score = clusters[i].affinity_with(clusters[j])
                if score > best_score:
                    best_score = score
                    best_pair = (i, j)

        # Merge j into i
        i, j = best_pair
        clusters[i].merge(clusters[j])
        clusters.pop(j)

    small_groups = [
        MergeGroup(
            name=c.name,
            files=c.files,
            total_size=c.total_size,
            keyword_score=1.0,
        )
        for c in clusters
    ]

    all_groups = large_groups + small_groups
    all_groups.sort(key=lambda g: g.name)

    return MergePlan(
        groups=all_groups,
        raw_count=len(files),
        merged_count=len(all_groups),
        target_count=target_count,
        tier_limit=tier_limit,
        skipped_large=len(large_files),
    )


def execute_merge(plan: MergePlan, output_dir: Path) -> list[Path]:
    """Execute a merge plan, writing concatenated files to output_dir.
    
    Args:
        plan: MergePlan from plan_merge().
        output_dir: Directory to write merged files to.

    Returns:
        List of paths to written files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for i, group in enumerate(plan.groups):
        parts = []
        total_size = 0
        for fp in sorted(group.files):
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                # Add section header
                rel = fp.name
                parts.append(f"\n\n---\n## Source: {rel}\n\n")
                parts.append(content)
                total_size += len(content.encode("utf-8"))
            except (OSError, IOError) as e:
                parts.append(f"\n\n*[Error reading {fp.name}: {e}]*\n")

        # Determine output name
        out_name = f"{i+1:02d}-{group.name[:60]}.md"
        out_path = output_dir / out_name

        content = "".join(parts)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(out_path)

    return written


def print_plan_summary(plan: MergePlan):
    """Print a human-readable summary of a merge plan."""
    print(_("merger_planning",
            count=plan.raw_count,
            tier=detect_tier()[0].upper(),
            limit=plan.tier_limit))
    print()

    if plan.skipped_large > 0:
        print(_("merger_auto_individual", count=plan.skipped_large))

    merged_small = plan.raw_count - plan.skipped_large
    merged_groups = plan.merged_count - plan.skipped_large
    if merged_small > 0:
        print(_("merger_auto_merged", count=merged_small, groups=merged_groups))

    print()
    pct = int(plan.merged_count / plan.tier_limit * 100) if plan.tier_limit > 0 else 80
    print(_("merger_target",
            target=plan.target_count,
            pct=pct,
            limit=plan.tier_limit))
    print()

    # Print groups
    print(_("source_plan_header", count=plan.raw_count))
    for i, g in enumerate(plan.groups, 1):
        size_kb = g.total_size / 1024
        n_files = len(g.files)
        print(_("source_plan_group",
                i=i,
                name=g.name[:50],
                files=n_files,
                size=f"{size_kb:.0f}"))
    print()
    print(_("source_plan_final",
            merged=plan.merged_count,
            target=plan.target_count,
            tier=detect_tier()[0].upper()))
