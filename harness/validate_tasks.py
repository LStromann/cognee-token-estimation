"""Check task files against the schema and the sizing plan in config/experiment.yaml."""
from collections import Counter
from harness.config import ROOT, load_config, load_tasks

REQUIRED = ["id", "topic", "type", "turns", "grader"]
TYPES = {"recall", "cross_source", "temporal", "action", "codebase_qa", "code_fix", "multi_turn", "control"}


def main():
    cfg = load_config()
    tasks = load_tasks()
    errors, ids = [], Counter(t.get("id") for t in tasks)
    for t in tasks:
        for k in REQUIRED:
            if k not in t:
                errors.append(f"{t['_file']}: missing {k}")
        if t.get("type") not in TYPES:
            errors.append(f"{t['_file']}: bad type {t.get('type')}")
        if t.get("type") == "multi_turn" and len(t.get("turns", [])) < 2:
            errors.append(f"{t['_file']}: multi_turn needs >=2 turns")
        g = t.get("grader") or {}
        kind = g.get("kind")
        if kind == "llm_judge" and not t.get("gold"):
            errors.append(f"{t['_file']}: llm_judge needs gold")
        if kind == "llm_judge" and not g.get("rubric"):
            errors.append(f"{t['_file']}: llm_judge needs rubric")
        if kind == "state_check" and not g.get("checks"):
            errors.append(f"{t['_file']}: state_check needs checks")
        if kind == "tests":
            hidden = ROOT / g.get("hidden_tests", "")
            if not hidden.is_dir() or not any(hidden.glob("test_*.py")):
                errors.append(f"{t['_file']}: hidden tests missing at {g.get('hidden_tests')}")
            if not g.get("command"):
                errors.append(f"{t['_file']}: tests grader needs command")
        if "hops" not in t:
            errors.append(f"{t['_file']}: missing hops")
    errors += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    have = Counter((t["topic"], t["type"]) for t in tasks)
    print(f"{'topic':<12}{'type':<14}{'have':>6}{'plan':>6}")
    for topic, plan in cfg["sizing"].items():
        for typ, n in plan.items():
            got = have[(topic, typ)]
            print(f"{topic:<12}{typ:<14}{got:>6}{n:>6}")
            if got != n:
                errors.append(f"{topic}/{typ}: have {got}, plan {n}")
    planned = sum(sum(p.values()) for p in cfg["sizing"].values())
    print(f"\nTOTAL {len(tasks)}/{planned} tasks.")
    print(f"Runs per model: {planned} tasks x {len(cfg['arms'])} arms x {cfg['repetitions']} reps = "
          f"{planned * len(cfg['arms']) * cfg['repetitions']}  | models: {len(cfg['models'])}")
    for e in errors:
        print("ERROR", e)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
