"""Strict output contracts, also checked locally without extra dependencies."""


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def arr(items):
    return {"type": "array", "items": items}


STRING = {"type": "string"}
STRINGS = arr(STRING)
ACTION = obj({"tool": {"type": "string", "enum": ["search", "lookup", "neighbors", "linked"]},
              "query": STRING, "regulation": STRING, "location": STRING, "evidence_id": STRING})
PLAN = obj({"issues": STRINGS, "missing_evidence": STRINGS, "ready": {"type": "boolean"}, "actions": arr(ACTION)})
SUPPORT = obj({"evidence_id": STRING, "quote": STRING})
CLAIM = obj({"id": STRING, "issue": STRING, "category": {"type": "string", "enum": ["direct_answer", "legal_requirement", "responsibility", "practical_step"]},
             "statement": STRING, "conditions": STRINGS, "supports": arr(SUPPORT)})
ASSESSMENT = obj({"claims": arr(CLAIM), "unknown_facts": STRINGS,
                  "verification_needed": STRINGS, "unanswered_issues": STRINGS})
REVIEW = obj({"verdicts": arr(obj({"claim_id": STRING, "supported": {"type": "boolean"}, "problem": STRING})),
              "coverage_gaps": STRINGS, "follow_up_actions": arr(ACTION)})


def validate(value, schema, path="response"):
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict) or set(value) != set(schema["required"]):
            raise ValueError(f"{path}: incorrect object keys")
        for name, sub in schema["properties"].items():
            validate(value[name], sub, f"{path}.{name}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) > 100:
            raise ValueError(f"{path}: expected bounded list")
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{i}]")
    elif kind == "string":
        if not isinstance(value, str) or len(value) > 30000:
            raise ValueError(f"{path}: expected bounded string")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: invalid enum value")
    elif kind == "boolean" and not isinstance(value, bool):
        raise ValueError(f"{path}: expected boolean")
