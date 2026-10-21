import pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config(path="config/experiment.yaml"):
    cfg = yaml.safe_load((ROOT / path).read_text())
    cfg["arm_defs"] = {a: yaml.safe_load((ROOT / f"config/arms/{a}.yaml").read_text()) for a in cfg["arms"]}
    return cfg


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
        by = {}
        for t in sorted(tasks, key=lambda t: t["id"]):
            by.setdefault(t["topic"], []).append(t)
        tasks = [t for ts in by.values() for t in ts[:pilot_n]]
    return tasks


def load_warmup(topic):
    f = ROOT / "warmup" / topic / "sessions.yaml"
    return yaml.safe_load(f.read_text())["sessions"] if f.exists() else []
