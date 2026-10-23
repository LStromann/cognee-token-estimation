"""Paired analysis: cognee vs baseline per (model, task, rep), with Cognee's tokens separated.

  python -m analysis.analyze [--runs results/<name>/runs.jsonl]

Per pair (exact proxy counts, one tokenizer):
  base_total      = baseline Claude tokens
  claude_cognee   = Claude tokens in the cognee arm (includes everything Cognee adds to context)
  carried         = Cognee-injected context inside claude_cognee (first send + re-sends)
  tooldefs        = Cognee tool definitions inside claude_cognee (fixed per-request overhead)
  cognee_internal = Cognee's own LLM tokens during the task (retrieval), `tokens.net_sources`
  ingest_share    = Cognee's warm-up ingestion tokens / tasks in the topic (amortised)
  net_delta       = claude_cognee + cognee_internal + ingest_share - base_total
                  = exploration_delta + carried + tooldefs + cognee_internal + ingest_share
  exploration_delta = (claude_cognee - carried - tooldefs) - base_total  (what Cognee saved Claude)
Sources outside net_sources (e.g. OpenAI embeddings) are reported separately, never summed.
Negative = Cognee saves tokens. Means of the components sum to the mean net_delta.
"""
import argparse, json, pathlib
import numpy as np, pandas as pd
from harness.config import load_config, ROOT

KEYS = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]


def boot_ci(x, stat=np.median, n=2000, seed=0):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    return tuple(np.percentile([stat(rng.choice(x, len(x))) for _ in range(n)], [2.5, 97.5]))


def cognee_sources(cfg):
    return list(cfg["tokens"].get("net_sources") or [])


def other_sources(cfg):
    return [r["source"] for r in (cfg["tokens"].get("routes") or {}).values() if r["source"] not in cognee_sources(cfg)]


def headline(p, by):
    rows = []
    for key, g in p.groupby(by):
        ok = g[g.success_b & g.success_c]
        lo, hi = boot_ci(ok.net_delta_pct)
        rows.append({**dict(zip(by, key if isinstance(key, tuple) else (key,))),
                     "pairs": len(g), "both_pass": len(ok),
                     "succ_base": round(g.success_b.mean(), 2), "succ_cognee": round(g.success_c.mean(), 2),
                     "succ_delta": round(float(g.success_c.mean() - g.success_b.mean()), 2),
                     "median_base_tokens": _i(ok.base_total.median()),
                     "median_net_delta": _i(ok.net_delta.median()),
                     "median_net_delta_pct": _r(ok.net_delta_pct.median()),
                     "ci95_pct": f"[{lo:.1f}, {hi:.1f}]",
                     "median_delta_pct_excl_ingest": _r(ok.excl_ingest_delta_pct.median()),
                     "median_weighted_delta_pct": _r(ok.weighted_delta_pct.median())})
    return pd.DataFrame(rows)


def decomposition(p, by):
    rows = []
    for key, g in p.groupby(by):
        ok = g[g.success_b & g.success_c]
        rows.append({**dict(zip(by, key if isinstance(key, tuple) else (key,))), "n": len(ok),
                     "base_claude": _i(ok.base_total.mean()),
                     "exploration_delta": _i(ok.exploration_delta.mean()),
                     "+ carried_ctx (first)": _i(ok.carried_first.mean()),
                     "+ carried_ctx (resent)": _i(ok.carried_resent.mean()),
                     "+ tooldefs": _i(ok.tooldefs.mean()),
                     "+ cognee_internal": _i(ok.cognee_internal.mean()),
                     "+ ingest_share": _i(ok.ingest_share.mean()),
                     "= net_delta": _i(ok.net_delta.mean()),
                     "injected_unique": _i(ok.injected.mean()),
                     "carry_multiplier": _r(ok.carried.sum() / max(ok.injected.sum(), 1))})
    return pd.DataFrame(rows)


def _i(v):
    return None if pd.isna(v) else int(round(v))


def _r(v):
    return None if pd.isna(v) else round(float(v), 1)


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "results" / cfg["name"] / "runs.jsonl"))
    a = ap.parse_args()
    out = pathlib.Path(a.runs).parent
    w = cfg["tokens"]["weights"]
    csrc = cognee_sources(cfg)
    df = pd.read_json(a.runs, lines=True)
    osrc = other_sources(cfg)
    for c in [f"{s}_{k}" for s in ["claude"] + csrc + osrc for k in KEYS + ["total"]] + \
             ["cognee_ctx_carried", "cognee_ctx_first", "cognee_ctx_resent", "cognee_ctx_injected",
              "cognee_tooldefs_carried"]:
        if c not in df:
            df[c] = 0
    df = df.fillna({c: 0 for c in df.columns if c.startswith(("cognee_", "claude_"))})
    df["cognee_internal"] = sum(df[f"{s}_total"] for s in csrc)
    df["claude_weighted"] = sum(w[k] * df[f"claude_{k}"] for k in KEYS)
    df["cognee_internal_weighted"] = sum(w[k] * df[f"{s}_{k}"] for s in csrc for k in KEYS)

    # amortised ingestion per task (Cognee warm-up cost)
    ing_file = out / "ingest.json"
    ingest = json.loads(ing_file.read_text()) if ing_file.exists() else {}
    n_tasks = df.groupby("topic").task_id.nunique().to_dict()
    ing_tot = {t: sum((v.get("cognee", {}).get(s, {}) or {}).get("total", 0) for s in csrc) for t, v in ingest.items()}
    ing_w = {t: sum(w[k] * ((v.get("cognee", {}).get(s, {}) or {}).get(k, 0) or 0) for s in csrc for k in KEYS)
             for t, v in ingest.items()}
    share = lambda tot: df.apply(lambda r: tot.get(r.topic, 0) / n_tasks.get(r.topic, 1) if r.arm == "cognee" else 0, axis=1)
    df["ingest_share"], df["ingest_share_weighted"] = share(ing_tot), share(ing_w)

    key = ["model", "task_id", "rep", "topic", "type"]
    b = df[df.arm == "baseline"].set_index(key)
    c = df[df.arm == "cognee"].set_index(key)
    p = pd.DataFrame(index=b.index.intersection(c.index))
    p["success_b"], p["success_c"] = b.success.astype(bool), c.success.astype(bool)
    p["base_total"] = b.claude_total + b.cognee_internal
    p["claude_cognee"] = c.claude_total
    p["carried"], p["carried_first"], p["carried_resent"] = c.cognee_ctx_carried, c.cognee_ctx_first, c.cognee_ctx_resent
    p["injected"] = c.cognee_ctx_injected
    p["tooldefs"] = c.cognee_tooldefs_carried
    p["cognee_internal"] = c.cognee_internal
    p["ingest_share"] = c.ingest_share
    p["exploration_delta"] = (p.claude_cognee - p.carried - p.tooldefs) - p.base_total
    for s_ in osrc:
        p[f"{s_}_separate"] = c[f"{s_}_total"]
    p["net_delta"] = p.claude_cognee + p.cognee_internal + p.ingest_share - p.base_total
    p["net_delta_pct"] = 100 * p.net_delta / p.base_total.replace(0, np.nan)
    base_w = b.claude_weighted + b.cognee_internal_weighted
    p["excl_ingest_delta_pct"] = 100 * (p.net_delta - p.ingest_share) / p.base_total.replace(0, np.nan)
    p["weighted_delta_pct"] = 100 * (c.claude_weighted + c.cognee_internal_weighted + c.ingest_share_weighted - base_w) / base_w.replace(0, np.nan)
    p = p.reset_index()
    p.to_csv(out / "pairs.csv", index=False)

    # break-even: how many tasks until ingestion is paid back
    be = []
    for t, g in p[p.success_b & p.success_c].groupby("topic"):
        per_task = (g.net_delta - g.ingest_share).mean()
        be.append({"topic": t, "ingest_tokens": int(ing_tot.get(t, 0)),
                   "mean_delta_per_task_excl_ingest": _i(per_task),
                   "break_even_tasks": _i(ing_tot.get(t, 0) / -per_task) if per_task < 0 else "never"})

    if "dry_run" not in df.columns:
        df["dry_run"] = False
    if "judge_disagreement" not in df.columns:
        df["judge_disagreement"] = False
    synthetic = bool(df["dry_run"].fillna(False).astype(bool).any())
    flags = int(df.get("token_crosscheck_flag", pd.Series(dtype=bool)).fillna(False).sum())
    missing = int(sum(df.get(f"{s}_usage_missing", pd.Series(0)).sum() for s in ["claude"] + csrc + osrc))
    unmatched = int(df.get("cognee_hook_unmatched", pd.Series(0)).fillna(0).sum())
    disagree = df[df["judge_disagreement"].fillna(False).astype(bool)].copy()
    disagree_cols = [c for c in
                     ["task_id", "model", "arm", "rep", "success", "secondary_success",
                      "grade_reason", "secondary_reason"]
                     if c in disagree.columns]
    disagree_md = "(none)" if disagree.empty else disagree[disagree_cols].to_markdown(index=False)
    banner = []
    if synthetic:
        banner = [
            "> **SYNTHETIC DRY-RUN.** These numbers come from the fake LLM backend "
            "(`harness/fake_upstream.py`, `harness/fake_claude.py`). They are not Cognee token savings. "
            "The stand-in agent uses a fixed call pattern (baseline: 4 Claude calls; cognee: 2 Claude calls "
            "plus 1 internal call) so every `net_delta` term is non-zero. It does not actually skip exploration. "
            "Do not cite this report as a result.",
            "",
        ]
    parts = ["# Results: cognee vs baseline",
             *banner,
             "Negative = Cognee saves tokens. Only pairs where both arms pass count toward token deltas.",
             "Coding tasks are inside this headline, on the same formula as project_ops and meetings.",
             "",
             "## Headline", headline(p, ["model"]).to_markdown(index=False), "",
             "## Where the tokens go (means, cognee arm minus baseline)",
             "`exploration_delta + carried_ctx + tooldefs + cognee_internal + ingest_share = net_delta`. "
             "`carry_multiplier` = how often each injected Cognee token is re-billed in Claude's context.", "",
             decomposition(p, ["model"]).to_markdown(index=False), "",
             "## By topic", headline(p, ["model", "topic"]).to_markdown(index=False), "",
             decomposition(p, ["model", "topic"]).to_markdown(index=False), "",
             "## By task type", headline(p, ["model", "type"]).to_markdown(index=False), "",
             "## Cognee ingestion and break-even", pd.DataFrame(be).to_markdown(index=False), "",
             *([f"## Reported separately (different tokenizer, not in net_delta)",
                p.groupby("model")[[f"{s_}_separate" for s_ in osrc]].median().round(0).to_markdown(), ""] if osrc else []),
             "## Judge disagreements",
             "Primary judge versus the secondary model. A row appears only when both verdicts succeeded and differ. "
             "Review the gold for these tasks. A transport or parse error is not a flag.",
             "",
             disagree_md, "",
             "## Data quality",
             f"- runs where proxy and stream-json disagree by more than {cfg['tokens']['crosscheck_tolerance']:.0%}: {flags}",
             f"- API responses without usage (check proxy parsing for that provider): {missing}",
             f"- logged Cognee hook texts not found in Claude's requests: {unmatched}",
             f"- runs flagged for judge disagreement: {len(disagree)}"]
    (out / "report.md").write_text("\n".join(parts))
    print("\n".join(parts))


if __name__ == "__main__":
    main()
