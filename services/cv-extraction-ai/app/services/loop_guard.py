"""Incremental detection and recovery of degenerate JSON output (feature 008).

Degenerate = one string value longer than ``max_string_chars`` (longest legit value in the
labels: ~1,500 chars) or the same string (>= 15 chars) ``max_repeats`` times in the SAME list.
Repeats across different lists are normal (a technology in skills and in several tech stacks);
repeats inside one list never occur in the 830 labels of dataset v3.
"""

import json

from json_repair import loads


class LoopGuard:
    def __init__(self, max_string_chars: int, max_repeats: int):
        self.max_string_chars = max_string_chars
        self.max_repeats = max_repeats
        self.reason: str | None = None
        self._stack = []
        self._in_string = False
        self._escaped = False
        self._is_key = False
        self._chars = []
        self._length = 0
        self._unicode_digits = 0

    def feed(self, chunk: str) -> bool:
        if self.reason:
            return True
        for char in chunk:
            if self._in_string:
                if self._unicode_digits:
                    self._chars.append(char)
                    self._unicode_digits -= 1
                elif self._escaped:
                    self._chars.append(char)
                    self._escaped = False
                    self._length += 1
                    if char == 'u':
                        self._unicode_digits = 4
                elif char == "\\":
                    self._chars.append(char)
                    self._escaped = True
                elif char == '"':
                    self._in_string = False
                    if not self._is_key:
                        raw = ''.join(self._chars)
                        try:
                            value = json.loads('"' + raw + '"').strip()
                        except ValueError:
                            value = raw.strip()
                        if len(value) >= 15 and self._stack and self._stack[-1][0] == '[':
                            counts = self._stack[-1][2]
                            count = counts.get(value, 0) + 1
                            counts[value] = count
                            if count >= self.max_repeats:
                                self.reason = "repeated_value"
                                return True
                    continue
                else:
                    self._chars.append(char)
                    self._length += 1
                if not self._is_key and self._length > self.max_string_chars:
                    self.reason = "long_string"
                    return True
            elif char == '"':
                self._in_string = True
                self._escaped = False
                self._chars = []
                self._length = 0
                self._unicode_digits = 0
                self._is_key = bool(self._stack and self._stack[-1][0] == '{' and self._stack[-1][1])
            elif char in '{[':
                self._stack.append([char, char == '{', {}])
            elif char in '}]':
                if self._stack:
                    self._stack.pop()
            elif char == ':' and self._stack and self._stack[-1][0] == '{':
                self._stack[-1][1] = False
            elif char == ',' and self._stack and self._stack[-1][0] == '{':
                self._stack[-1][1] = True
        return False


def salvage(text: str) -> dict | None:
    in_string = escaped = False
    string_start = None
    for i, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            string_start = i
    if in_string:
        text = text[:string_start]
    try:
        result = loads(text)
    except (ValueError, TypeError, RecursionError):
        return None
    from app.utils.json_parse import merge_fragments

    result = merge_fragments(result)
    if result is None:
        return None

    def deduplicate(value):
        if isinstance(value, dict):
            return {key: deduplicate(item) for key, item in value.items()}
        if isinstance(value, list):
            result = []
            strings = set()
            dicts = set()
            for item in value:
                item = deduplicate(item)
                if isinstance(item, str):
                    if item in strings:
                        continue
                    strings.add(item)
                elif isinstance(item, dict):
                    key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    if key in dicts:
                        continue
                    dicts.add(key)
                result.append(item)
            return result
        return value

    return deduplicate(result)
