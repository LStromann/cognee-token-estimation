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


def _judge_prompt(task, answer):
    return JUDGE.format(
        prompt=" / ".join(task["turns"]), gold=task.get("gold", ""),
        rubric=task["grader"].get("rubric", "Pass if consistent with the reference."), answer=answer)


def _parse_verdict(text):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        v = json.loads(m.group(0))
        return {"success": bool(v.get("pass")), "grade_reason": v.get("reason", ""), "error": None}
    except Exception:
        return {"success": False, "grade_reason": f"judge parse error: {text[:200]}", "error": None}


def llm_judge(task, answer, judge_model, base_url=None):
    import anthropic
    msg = anthropic.Anthropic(base_url=base_url).messages.create(
        model=judge_model, max_tokens=300,
        messages=[{"role": "user", "content": _judge_prompt(task, answer)}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    parsed = _parse_verdict(text)
    return {"success": parsed["success"], "grade_reason": parsed["grade_reason"]}


def _openai_url(base):
    base = base.rstrip("/")
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def secondary_judge(task, answer, spec, direct_base=None):
    """Second grader from another model family. None when disabled.

    A transport or parse failure is recorded as error and is not a disagreement:
    only two successful verdicts that differ raise judge_disagreement.
    """
    if not spec or not spec.get("enabled", False):
        return None
    if task.get("grader", {}).get("kind") != "llm_judge":
        return None
    prompt = _judge_prompt(task, answer)
    model = spec.get("model") or "gpt-4.1-mini"
    try:
        if spec.get("provider", "openai") == "anthropic":
            import anthropic
            msg = anthropic.Anthropic(base_url=spec.get("base_url") or direct_base).messages.create(
                model=model, max_tokens=300, messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in msg.content if b.type == "text")
        else:
            import os
            import urllib.request
            key = os.environ.get(spec.get("api_key_env") or "OPENAI_API_KEY", "")
            if not key:
                return {"success": None, "reason": "", "error": f"{spec.get('api_key_env') or 'OPENAI_API_KEY'} is unset"}
            body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                               "max_tokens": 300}).encode()
            req = urllib.request.Request(
                _openai_url(spec.get("base_url") or "https://api.openai.com/v1"), data=body,
                headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=float(spec.get("timeout_s") or 60)) as resp:
                payload = json.loads(resp.read().decode())
            text = payload["choices"][0]["message"]["content"]
    except Exception as exc:
        return {"success": None, "reason": "", "error": f"{type(exc).__name__}: {exc}"}
    parsed = _parse_verdict(text)
    if parsed["grade_reason"].startswith("judge parse error"):
        return {"success": None, "reason": parsed["grade_reason"], "error": parsed["grade_reason"]}
    return {"success": parsed["success"], "reason": parsed["grade_reason"], "error": None}
