import json, re, shutil, subprocess
from harness.config import ROOT


def grade(task, answer, slot, judge_model, base_url=None):
    g = task["grader"]
    kind = g["kind"]
    if kind == "contains":
        a = answer.lower()
        ok = all(str(v).lower() in a for v in g["values"])
        return {"success": ok, "grade_reason": "contains" if ok else "missing values"}
    if kind == "state_check":
        return state_check(g["checks"], slot)
    if kind == "tests":
        return run_tests(g, slot)
    if kind == "llm_judge":
        return llm_judge(task, answer, judge_model, base_url)
    raise ValueError(f"unknown grader {kind}")


def state_check(checks, slot):
    from mcp_mocks.common import match
    for c in checks:
        data = json.loads((slot / "state" / c["server"] / "data.json").read_text())
        items = data[c["collection"]]
        if c.get("created_in_run"):
            items = [i for i in items if i.get("created_in_run")]
        if c.get("updated_in_run"):
            items = [i for i in items if i.get("updated_in_run") or i.get("created_in_run")]
        if not any(match(i, c.get("where", {})) for i in items):
            return {"success": False, "grade_reason": f"no match for {c}"}
    return {"success": True, "grade_reason": "all checks matched"}


def run_tests(g, slot):
    ws = slot / "workspace"
    dst = ws / "tests" / "hidden"
    shutil.copytree(ROOT / g["hidden_tests"], dst, dirs_exist_ok=True)
    p = subprocess.run(g["command"], shell=True, cwd=ws, capture_output=True, text=True, timeout=900)
    return {"success": p.returncode == 0, "grade_reason": p.stdout[-400:]}


JUDGE = """You are grading an AI assistant's answer.
Task: {prompt}
Reference answer: {gold}
Rubric: {rubric}
Assistant's final answer:
<answer>
{answer}
</answer>
Reply with JSON only: {{"pass": true|false, "reason": "<one sentence>"}}"""


def llm_judge(task, answer, judge_model, base_url=None):
    import anthropic
    msg = anthropic.Anthropic(base_url=base_url).messages.create(
        model=judge_model, max_tokens=300,
        messages=[{"role": "user", "content": JUDGE.format(
            prompt=" / ".join(task["turns"]), gold=task.get("gold", ""),
            rubric=task["grader"].get("rubric", "Pass if consistent with the reference."), answer=answer)}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        v = json.loads(m.group(0))
        return {"success": bool(v.get("pass")), "grade_reason": v.get("reason", "")}
    except Exception:
        return {"success": False, "grade_reason": f"judge parse error: {text[:200]}"}
