import pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config(path="config/experiment.yaml"):
    import os
    cfg = yaml.safe_load((ROOT / path).read_text())
    cfg["arm_defs"] = {a: yaml.safe_load((ROOT / f"config/arms/{a}.yaml").read_text()) for a in cfg["arms"]}
    if os.environ.get("CTB_WORK_DIR"):
        cfg["work_dir"] = os.environ["CTB_WORK_DIR"]
    if os.environ.get("CTB_RESULT_NAME"):
        cfg["name"] = os.environ["CTB_RESULT_NAME"]
    return cfg


# Pilot spreads across types. Sorting by id and taking the first N would be five
# recalls once the catalog is full, which would not exercise the graders.
TYPE_ORDER = ["action", "code_fix", "codebase_qa", "control", "cross_source", "multi_turn", "recall", "temporal"]


def _pilot(tasks, n):
    by_topic = {}
    for t in tasks:
        by_topic.setdefault(t["topic"], []).append(t)
    picked = []
    for ts in by_topic.values():
        groups = {}
        for t in sorted(ts, key=lambda item: item["id"]):
            groups.setdefault(t["type"], []).append(t)
        order = [typ for typ in TYPE_ORDER if typ in groups]
        index = {typ: 0 for typ in order}
        chosen = []
        while len(chosen) < n and order:
            for typ in list(order):
                i = index[typ]
                if i < len(groups[typ]):
                    chosen.append(groups[typ][i])
                    index[typ] = i + 1
                    if len(chosen) >= n:
                        break
                else:
                    order.remove(typ)
        picked.extend(chosen)
    return picked


def load_tasks(topics=None, pilot_n=None):
    tasks = []
    for f in sorted((ROOT / "tasks").glob("*/*.yaml")):
        if "TEMPLATE" in f.name:
            continue
        t = yaml.safe_load(f.read_text())
        t["_file"] = str(f.relative_to(ROOT))
        tasks.append(t)
    if topics:
        tasks = [t for t in tasks if t["topic"] in topics]
    if pilot_n:
        tasks = _pilot(tasks, pilot_n)
    return tasks


def load_warmup(topic):
    f = ROOT / "warmup" / topic / "sessions.yaml"
    return yaml.safe_load(f.read_text())["sessions"] if f.exists() else []
