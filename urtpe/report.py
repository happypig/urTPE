"""Review report generation: auto-fix summary, flags, parse errors."""

from __future__ import annotations

from urtpe.models import CleanRecord, Project, RawRecord


def recovery_report(outcome) -> list[str]:
    """The RECOVERED / INCOMPLETE section (D7).

    Both lines appear whenever either count is non-zero, each row named with its
    provenance (D7's scenario pins ``RECOVERED: 14 …`` per-row naming). The
    not-a-faithful-copy statement rides both branches: recovered rows are
    restored from outside the PDF, so a recovered gazette is no more a faithful
    copy than an excluded one.
    """
    recovered = list(outcome.recovered)
    residuals = list(outcome.residuals)
    if not recovered and not residuals:
        return []
    lines = [f"RECOVERED: {len(recovered)} 筆 (publisher-truncated rows "
             "re-identified via the city's case APIs and map service)"]
    for rec in recovered:
        prov = rec.get("recovery") or {}
        flags = prov.get("flags") or {}
        bits = [f"cases {','.join(prov.get('cases') or []) or '?'}"]
        if prov.get("api_cases"):
            bits.append(f"api {','.join(prov['api_cases'])}")
        bits += [f"date {prov.get('date_result', '?')} ({prov.get('date_field', '?')})",
                 f"list {prov.get('list_source', '?')}"]
        extra = [k for k in ("ambiguous-zone", "date-pm1", "similarity-band")
                 if flags.get(k)]
        if extra:
            bits.append("flags " + ",".join(extra))
        if flags.get("normalized"):
            bits.append("normalized " + ";".join(flags["normalized"]))
        lines.append(f"  編號 {rec.get('recno')}: " + ", ".join(bits))
    lines.append(f"INCOMPLETE: {len(residuals)} 筆 (still excluded; this gazette "
                 "is NOT a faithful copy of the publication)")
    for rec in residuals:
        lines.append(f"  編號 {rec.get('recno')}: {rec.get('parse_error', '')}")
    return lines


def review_report(
    raw: list[RawRecord],
    clean: list[CleanRecord],
    projects: list[Project],
    link_threshold: float,
    flag_threshold: float,
    ledger_outcome=None,
    reconciliation=None,
    tripwire=None,
    recovery=None,
) -> str:
    lines: list[str] = []

    if tripwire is not None:
        lines.append(tripwire.report())
        lines.append("")

    if reconciliation is not None:
        lines.append(reconciliation.report())
        lines.append("")

    if recovery is not None:
        lines.extend(recovery_report(recovery))
        lines.append("")

    errs = [r for r in raw if r.parse_error]
    lines.append(f"解析缺漏記錄: {len(errs)} 筆")
    for r in errs:
        lines.append(f"  編號 {r.recno}: {r.parse_error}")

    if ledger_outcome is not None:
        lines.append("")
        lines.append(ledger_outcome.report())

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