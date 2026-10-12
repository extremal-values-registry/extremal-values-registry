"""Shared helpers: load entries, a small JSON-Schema subset checker, numeric parsing. Stdlib only."""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES = os.path.join(ROOT, "data", "entries.jsonl")
SCHEMA = os.path.join(ROOT, "schema.json")

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def dump_jsonl(rows):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _is_type(v, t):
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def check(value, schema, path="$"):
    """Return a list of error strings. Supports type, enum, required, properties,
    additionalProperties=false, items, pattern (strings only), minLength."""
    errs = []
    if "enum" in schema and value not in schema["enum"]:
        errs.append("%s: %r not in %r" % (path, value, schema["enum"]))
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, t) for t in types):
            return errs + [
                "%s: expected %s, got %s" % (path, types, type(value).__name__)
            ]
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append("%s: %r does not match %s" % (path, value, schema["pattern"]))
        if len(value) < schema.get("minLength", 0):
            errs.append("%s: too short" % path)
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append("%s: missing %s" % (path, k))
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errs += check(v, props[k], "%s.%s" % (path, k))
            elif schema.get("additionalProperties") is False:
                errs.append("%s: unexpected field %s" % (path, k))
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errs += check(v, schema["items"], "%s[%d]" % (path, i))
    return errs


NUM = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")


def num(s):
    if isinstance(s, bool) or s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    m = NUM.match(str(s))
    return float(m.group(1)) if m else None


def strictly_better(direction, new, old):
    a, b = num(new), num(old)
    if a is None or b is None or direction not in ("min", "max"):
        return False
    return a < b if direction == "min" else a > b
