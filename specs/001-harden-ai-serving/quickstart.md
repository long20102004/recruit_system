# Quickstart / Verification: feature 001

```bash
cd ai-service
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q            # offline, no model needed, < 60 s
```

Manual smoke (needs model; GGUF engine needs llama-cpp-python):

```bash
.venv/bin/python main.py &
curl -s localhost:8000/health            # engine=llama_cpp, model=.../merged_model/model.gguf
                                         # or fallback_reason explains why not
curl -s -D- -X POST localhost:8000/api/v1/extract-cv \
  -H 'Content-Type: application/json' \
  -d '{"cv_text":"Họ tên: Nguyễn Văn Test\nEmail: test.synthetic@example.com"}'
# → 200 + X-Request-ID; server log has no "test.synthetic@example.com"
```

Install GGUF runtime with CUDA (environment change, needs approval):

```bash
CMAKE_ARGS="-DGGML_CUDA=on" .venv/bin/pip install llama-cpp-python
```
