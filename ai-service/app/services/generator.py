import json
import threading
import time
from dataclasses import dataclass

from app.core import config
from app.core.errors import InputTooLongError, ModelBusyError
from app.core.logging import logger
from app.services.model_loader import state
from app.services.loop_guard import LoopGuard, salvage
from app.services.prompt import build_prompt_gguf
from app.services import prompt_v2, prompt_v3
from app.services.continuation import merge_outputs, plan_continuation
from app.utils.json_parse import extract_json

_lock = threading.Lock()


@dataclass
class GenerationResult:
    text: str
    truncated: bool
    reason: str | None
    output_tokens: int | None
    continued: bool = False
    continuation_reason: str | None = None


def build_prompt(cv_text: str) -> str:
    if config.PROMPT_VERSION in ("v3", "v4", "v5"):  # v4, v5 = prompt v3, retrained models
        return prompt_v3.render_prompt(cv_text)
    if config.PROMPT_VERSION == "v2":
        return prompt_v2.render_prompt(cv_text)
    return build_prompt_gguf(cv_text)


def count_prompt_tokens(prompt: str) -> int:
    if state.engine == "llama_cpp":
        return len(state.llm.tokenize(prompt.encode("utf-8"), add_bos=False, special=True))
    return len(state.tokenizer(prompt, add_special_tokens=False)["input_ids"])


def _generate_llama(prompt: str, *, max_tokens: int | None = None,
                    prefix: str = "", continue_output: bool = False) -> GenerationResult:
    logger.info("Inference bằng llama.cpp (GGUF)...")
    start = time.time()
    resp = state.llm(
        prompt=prompt,
        max_tokens=config.MAX_NEW_TOKENS if max_tokens is None else max_tokens,
        temperature=0.0,
        repeat_penalty=1.0,
        stop=["<|im_end|>", "<|endoftext|>", "</think>"],
        stream=True,
    )
    guard = LoopGuard(config.LOOP_MAX_STRING_CHARS, config.LOOP_MAX_REPEATS)
    if prefix:
        guard.feed(prefix)
    parts = []
    reason = None
    output_tokens = None
    if isinstance(resp, dict):
        choice = resp["choices"][0]
        parts.append(choice.get("text", ""))
        output_tokens = resp.get("usage", {}).get("completion_tokens")
        if choice.get("finish_reason") == "length":
            reason = "max_tokens"
    else:
        output_tokens = 0
        guard_started = bool(prefix)
        try:
            for chunk in resp:
                choice = chunk["choices"][0]
                text = choice.get("text", "")
                if text:
                    output_tokens += 1
                if not guard_started and text.strip():
                    if not text.lstrip().startswith("{"):
                        guard.feed("{")
                    guard_started = True
                # A chunk can contain text past the guard's stopping point.
                # Retain only consumed characters, not an already closed but
                # degenerate object that happened to arrive in the same chunk.
                for index, char in enumerate(text):
                    if guard.feed(char):
                        parts.append(text[:index + 1])
                        break
                else:
                    parts.append(text)
                if guard.reason:
                    reason = guard.reason
                    break
                if choice.get("finish_reason") == "length":
                    reason = "max_tokens"
                    break
        finally:
            close = getattr(resp, "close", None)
            if close:
                close()
    duration = time.time() - start
    raw_output = prefix + ''.join(parts).strip()
    logger.info(f"Output tokens: {output_tokens if output_tokens is not None else '?'}; reason: {reason}")
    logger.info(f"Inference time: {duration:.2f}s")
    logger.info(f"Raw output length: {len(raw_output)} chars")

    # Prompt đã mớm '{' nên ghép lại vào đầu output nếu thiếu
    if not raw_output.startswith("{"):
        raw_output = "{\n" + raw_output

    # Plan on the original stream, before salvage can retain partial entries.
    first_raw = raw_output
    if reason:
        repaired = salvage(raw_output)
        if repaired is not None:
            raw_output = json.dumps(repaired, ensure_ascii=False)
    result = GenerationResult(raw_output, reason is not None, reason, output_tokens)
    if continue_output:
        return _continue_llama(prompt, first_raw, result)
    return result


def _continue_llama(prompt: str, raw_text: str, first: GenerationResult) -> GenerationResult:
    try:
        plan = plan_continuation(raw_text, first.reason)
        if plan is None:
            return first
        prefix, next_key = plan
        seed = prefix + ',"' + next_key + '":'
        continuation_prompt = prompt + seed
        input_tokens = count_prompt_tokens(continuation_prompt)
        remaining = (state.context_tokens or config.CONTEXT_TOKENS) - input_tokens
        if remaining <= 0:
            logger.info("Continuation skipped: context budget exhausted; input_tokens=%s", input_tokens)
            return first
        budget = min(config.MAX_NEW_TOKENS, remaining)
        continuation_reason = first.reason or "missing_tail"
        logger.info("Continuation: reason=%s; input_tokens=%s; max_tokens=%s",
                    continuation_reason, input_tokens, budget)
        second = _generate_llama(continuation_prompt, max_tokens=budget, prefix=seed)
        first_data = extract_json(first.text)
        second_data = extract_json(second.text)
        if not isinstance(first_data, dict) or not isinstance(second_data, dict):
            return first
        return GenerationResult(
            json.dumps(merge_outputs(first_data, second_data), ensure_ascii=False),
            first.truncated, first.reason,
            ((first.output_tokens + second.output_tokens)
             if first.output_tokens is not None and second.output_tokens is not None else None),
            continued=True, continuation_reason=continuation_reason,
        )
    except Exception:
        # Never expose model text or exception details containing CV content.
        logger.warning("Continuation failed; keeping first output")
        return first


def _generate_transformers(prompt: str) -> GenerationResult:
    import torch

    model = state.model
    tokenizer = state.tokenizer

    device = next(model.parameters()).device

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    input_tokens = inputs["input_ids"].shape[1]

    logger.info(f"Input tokens: {input_tokens}")

    start = time.time()

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=config.MAX_NEW_TOKENS,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.0,
        )

    duration = time.time() - start

    generated_tokens = outputs[0][input_tokens:]
    output_tokens = len(generated_tokens)

    raw_output = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    ).strip()

    if not raw_output.startswith("{"):
        raw_output = "{\n" + raw_output

    logger.info(f"Output tokens: {output_tokens}")
    logger.info(f"Inference time: {duration:.2f}s")
    logger.info(f"Raw output length: {len(raw_output)} chars")

    truncated = output_tokens >= config.MAX_NEW_TOKENS
    return GenerationResult(raw_output, truncated, "max_tokens" if truncated else None, output_tokens)


def generate_cv(cv_text: str) -> str:
    return generate_cv_result(cv_text).text


def generate_cv_result(cv_text: str) -> GenerationResult:
    prompt = build_prompt(cv_text)
    start_wait = time.monotonic()
    if not _lock.acquire(timeout=config.QUEUE_WAIT_SECONDS):
        raise ModelBusyError(time.monotonic() - start_wait)

    try:
        n = count_prompt_tokens(prompt)
        context = state.context_tokens or config.CONTEXT_TOKENS
        max_prompt = context - config.MAX_NEW_TOKENS
        if n > max_prompt:
            raise InputTooLongError(n, max_prompt)

        if state.engine == "llama_cpp":
            return _generate_llama(
                prompt, continue_output=config.CONTINUATION_ENABLED and config.PROMPT_VERSION != "v1",
            )
        return _generate_transformers(prompt)
    finally:
        _lock.release()
