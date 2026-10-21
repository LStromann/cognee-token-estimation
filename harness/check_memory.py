"""Show what native memory each warm-up snapshot contains (run after `make warmup`).

If the baseline has no native memory, the comparison is 'Cognee vs no memory', not
'Cognee vs Claude Code memory' -> fix warm-up (e.g. memory_prompting: explicit) first.
"""
import json
from harness import env
from harness.config import load_config


def main():
    cfg = load_config()
    bad = 0
    for arm in cfg["arms"]:
        for topic in cfg["topics"]:
            meta_f = env.snap_dir(cfg, arm, topic) / "meta.json"
            if not meta_f.exists():
                print(f"{arm:<9}{topic:<12} no snapshot")
                continue
            mem = env.memory_summary(env.snap_dir(cfg, arm, topic))
            bad += not mem["has_native_memory"]
            print(f"{arm:<9}{topic:<12} native_memory={mem['has_native_memory']!s:<6} "
                  f"CLAUDE.md changed={mem['claude_md_changed']!s:<6} files={len(mem['memory_files'])} "
                  f"bytes={mem['memory_bytes']}")
            for f in mem["memory_files"]:
                print(f"{'':<21}- {f}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
