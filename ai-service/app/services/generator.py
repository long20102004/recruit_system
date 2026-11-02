import time

from app.core.config import MAX_INPUT_TOKENS, MAX_NEW_TOKENS
from app.core.logging import logger
from app.services.model_loader import state
from app.services.prompt import build_prompt_gguf


def generate_cv(cv_text: str):
    prompt = build_prompt_gguf(cv_text)

    if state.engine == "llama_cpp":
        logger.info("Inference bằng llama.cpp (GGUF)...")
        start = time.time()
        resp = state.llm(
            prompt=prompt,
            max_tokens=MAX_NEW_TOKENS,
            temperature=0.0,
            repeat_penalty=1.0,
            stop=["<|im_end|>", "<|endoftext|>", "</think>"],
        )
        duration = time.time() - start
        raw_output = resp["choices"][0]["text"].strip()
        usage = resp.get("usage", {})
        logger.info(f"Input tokens: {usage.get('prompt_tokens', '?')}")
        logger.info(f"Output tokens: {usage.get('completion_tokens', '?')}")
        logger.info(f"Inference time: {duration:.2f}s")
        logger.info(f"Raw output length: {len(raw_output)} chars")

        # Prompt đã mớm '{' nên ghép lại vào đầu output nếu thiếu
        if not raw_output.startswith("{"):
            raw_output = "{\n" + raw_output

        return raw_output

    import torch

    model = state.model
    tokenizer = state.tokenizer

    device = next(model.parameters()).device

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_INPUT_TOKENS,
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
            max_new_tokens=MAX_NEW_TOKENS,
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

    return raw_output
