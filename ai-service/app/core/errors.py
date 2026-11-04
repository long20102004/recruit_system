class InputTooLongError(Exception):
    def __init__(self, prompt_tokens: int, max_prompt_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.max_prompt_tokens = max_prompt_tokens
        super().__init__(
            f"CV quá dài: {prompt_tokens} token, tối đa {max_prompt_tokens} token"
        )


class ModelBusyError(Exception):
    def __init__(self, waited_seconds: float) -> None:
        self.waited_seconds = waited_seconds
        super().__init__("Service đang bận, vui lòng thử lại sau")
