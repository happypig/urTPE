"""Review report generation: auto-fix summary, flags, parse errors."""

from __future__ import annotations

from urtpe.models import CleanRecord, Project, RawRecord


def review_report(
    raw: list[RawRecord],
    clean: list[CleanRecord],
    projects: list[Project],
    link_threshold: float,
    flag_threshold: float,
) -> str:
    lines: list[str] = []

    errs = [r for r in raw if r.parse_error]
    lines.append(f"解析缺漏記錄: {len(errs)} 筆")
    for r in errs:
        lines.append(f"  編號 {r.recno}: {r.parse_error}")

    fixed = [c for c in clean if c.auto_fixes]
    lines.append("")
    lines.append(f"自動修正記錄: {len(fixed)} 筆")
    for c in fixed:
        lines.append(f"  編號 {c.recno}: {', '.join(c.auto_fixes)}")

    flagged = [c for c in clean if c.review_flags]
    lines.append("")
    lines.append(f"需人工檢視記錄: {len(flagged)} 筆")
    for c in flagged:
        lines.append(f"  編號 {c.recno}: {', '.join(c.review_flags)}")

    singletons = [p for p in projects if len(p.members) == 1]
    multi = [p for p in projects if len(p.members) > 1]
    lines.append("")
    lines.append(f"專案家族: {len(projects)} (單筆 {len(singletons)}, 多筆 {len(multi)})")

    multi_sorted = sorted(multi, key=lambda p: len(p.members), reverse=True)
    lines.append("")
    lines.append(f"最大多筆家族（{len(multi_sorted)} 個，依成員數排序）:")
    for p in multi_sorted[:50]:
        recs = ",".join(str(m.recno) for m in sorted(p.members, key=lambda m: m.recno))
        lines.append(f"  {p.project_id}  [{recs}]")

    all_borderline = sorted(
        ((a, b, s) for p in projects for (a, b, s) in p.borderline),
        key=lambda t: t[2],
        reverse=True,
    )
    lines.append("")
    lines.append(f"臨界對(相似度 {flag_threshold}–{link_threshold}): {len(all_borderline)} 對")
    for a, b, s in all_borderline:
        lines.append(f"  編號 {a} ↔ {b}: {s}")

    lines.append("")
    lines.append(f"門檻: link >= {link_threshold}, flag >= {flag_threshold}")
    return "\n".join(lines) + "\n"