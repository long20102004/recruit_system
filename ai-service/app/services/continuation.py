"""Plan a single tail completion without retaining unfinished list entries."""

import json

TOP_KEYS = ["personal_info", "objective", "education", "experience", "personal_projects",
            "skills", "certificates", "honours", "languages"]


def _deduplicate(value):
    if isinstance(value, dict):
        return {key: _deduplicate(item) for key, item in value.items()}
    if isinstance(value, list):
        result = [_deduplicate(item) for item in value]
        while len(result) > 1 and result[-1] in result[:-1]:
            result.pop()
        return result
    return value


def plan_continuation(raw_text: str, truncated_reason: str | None) -> tuple[str, str] | None:
    text = raw_text.strip()
    if not text.startswith("{"):
        return None
    repeated = truncated_reason == "repeated_value"
    try:
        complete = json.loads(text)
    except ValueError:
        complete = None

    # Every checkpoint records a syntactically complete value and the containers
    # needed to close it. Ignore nested fields of an unfinished top-level item,
    # except for repeated strings, where retaining its first occurrence is safe.
    candidates = []
    stack = []
    in_string = escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
                if repeated or len(stack) == 1:
                    candidates.append((index + 1, stack.copy()))
            continue
        if char == '"':
            in_string = True
        elif char in "{[":
            stack.append(char)
            if len(stack) == 2:
                candidates.append((index + 1, stack.copy()))
        elif char in "}]":
            if not stack or (stack[-1], char) not in (("{", "}"), ("[", "]")):
                break
            stack.pop()
            if stack and (repeated or len(stack) <= 2):
                candidates.append((index + 1, stack.copy()))
        elif char == "," and len(stack) == 1:
            candidates.append((index, stack.copy()))

    if isinstance(complete, dict):
        candidates.append((len(text) - 1, ["{"]))
    elif stack == ["{"] and not in_string:
        # A complete scalar (e.g. null) may be followed only by a missing '}'.
        candidates.append((len(text), stack.copy()))

    for end, opened in reversed(candidates):
        suffix = "".join("]" if char == "[" else "}" for char in reversed(opened[1:]))
        prefix = text[:end] + suffix
        try:
            data = json.loads(prefix + "}")
        except ValueError:
            continue
        keys = [key for key in data if key in TOP_KEYS]
        if not keys:
            return None
        last_key = keys[-1]
        next_key = next((key for key in TOP_KEYS[TOP_KEYS.index(last_key) + 1:]
                         if key not in data), None)
        if next_key is None:
            return None
        if repeated:
            data = _deduplicate(data)
        # Canonicalisation also guarantees that prefix + '}' is valid JSON.
        return json.dumps(data, ensure_ascii=False)[:-1], next_key
    return None


def merge_outputs(first: dict, second: dict) -> dict:
    merged = dict(first)
    for key, value in second.items():
        if key not in merged or merged[key] in (None, [], ""):
            merged[key] = value
    return merged
