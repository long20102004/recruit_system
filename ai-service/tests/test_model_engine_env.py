import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app.core import config
from app.core import logging as service_logging
from app.services import model_loader


SERVICE_DIR = Path(__file__).resolve().parents[1]


LLAMA_CPP_STUB = '''"""Stub llama_cpp module so tests never load a real model."""
import json
import sys


class Llama:
    def __init__(self, *args, **kwargs):
        record = {k: kwargs.get(k) for k in ("model_path", "n_ctx")}
        with open(sys.argv[1], "w") as fh:
            json.dump(record, fh)
        raise AssertionError(f"autoselect sentinel: {json.dumps(record)}")
'''


def make_env_project(tmp_path, env_text):
    """Sandbox project với bản copy config.py/logging.py/model_loader.py.

    Cho phép test logic .env mà không tạo/đọc file .env thật của ai-service.
    """
    project = tmp_path / "project"
    core = project / "app" / "core"
    services = project / "app" / "services"
    core.mkdir(parents=True)
    services.mkdir(parents=True)
    shutil.copy(Path(config.__file__), core / "config.py")
    shutil.copy(Path(service_logging.__file__), core / "logging.py")
    shutil.copy(Path(model_loader.__file__), services / "model_loader.py")
    (project / ".env").write_text(env_text.strip() + "\n")
    return project


def run_cwd_isolated(project, cwd, code, extra_args=(), **overrides):
    """Chạy python với cwd khác thư mục project.

    `app` được import qua PYTHONPATH trỏ tới project nên .env vẫn được neo
    vào đúng project chứa bản copy config.py.
    """
    env = os.environ.copy()
    for key in ("PROMPT_VERSION", "MODEL_ENGINE", "LORA_PATH", "GGUF_MODEL_PATH", "MAX_NEW_TOKENS"):
        env.pop(key, None)
    env.update(overrides)
    env["PYTHONPATH"] = str(project)
    argv = [sys.executable, "-c", code, *extra_args]
    # cwd chứa llama_cpp.py stub để không cần llama-cpp-python thật.
    return subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True)


def config_subprocess(**overrides):
    env = os.environ.copy()
    for key in ("PROMPT_VERSION", "MODEL_ENGINE", "LORA_PATH", "GGUF_MODEL_PATH", "MAX_NEW_TOKENS"):
        env.pop(key, None)
    env.update(overrides)
    code = (
        "import json; from app.core import config as c; "
        "print(json.dumps([c.PROMPT_VERSION, c.MODEL_ENGINE, c.LORA_PATH, "
        "c.GGUF_MODEL_PATH, c.MAX_NEW_TOKENS]))"
    )
    return subprocess.run([sys.executable, "-c", code], cwd=SERVICE_DIR, env=env,
                          text=True, capture_output=True)


def test_config_defaults():
    result = config_subprocess()
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["v4", "transformers", "./checkpoint-v4",
                                         "./merged_model/model-v4-q4_k_m.gguf", 2048]


def test_config_override():
    result = config_subprocess(PROMPT_VERSION=" V1 ", MODEL_ENGINE=" LLAMA_CPP ",
                               LORA_PATH="custom/lora", GGUF_MODEL_PATH="custom/model.gguf")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["v1", "llama_cpp", "custom/lora", "custom/model.gguf", 1500]


def test_invalid_prompt_version():
    result = config_subprocess(PROMPT_VERSION="unknown")
    assert result.returncode != 0
    assert "PROMPT_VERSION must be" in result.stderr


def test_invalid_engine(monkeypatch):
    monkeypatch.setattr(config, "MODEL_ENGINE", "invalid")
    with pytest.raises(ValueError, match="MODEL_ENGINE"):
        model_loader.load_model()


def test_transformers_selected(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "MODEL_ENGINE", "transformers")
    monkeypatch.setattr(model_loader, "_load_transformers", lambda: calls.append("transformers"))
    monkeypatch.setattr(model_loader, "_load_llama_cpp", lambda: pytest.fail("unexpected GGUF load"))
    model_loader.load_model()
    assert calls == ["transformers"]


def test_gguf_relative_path_and_success(monkeypatch, tmp_path):
    gguf = tmp_path / "model.gguf"
    gguf.touch()
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "MODEL_ENGINE", "llama_cpp")
    monkeypatch.setattr(config, "GGUF_MODEL_PATH", "model.gguf")
    monkeypatch.setenv("GGUF_MODEL_PATH", "model.gguf")
    monkeypatch.chdir(tmp_path.parent)
    monkeypatch.setattr(model_loader, "_preload_cuda_libs", lambda: None)
    calls = []
    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(Llama=lambda **kw: calls.append(kw) or object()))
    model_loader.load_model()
    assert calls[0]["model_path"] == str(gguf)
    assert model_loader.state.engine == "llama_cpp"
    assert model_loader.state.gguf_path_used == str(gguf)


@pytest.mark.parametrize("failure", ["missing", "load"])
def test_gguf_failure_never_falls_back(monkeypatch, tmp_path, failure):
    gguf = tmp_path / "missing.gguf"
    if failure == "load":
        gguf.touch()
    monkeypatch.setattr(config, "MODEL_ENGINE", "llama_cpp")
    monkeypatch.setattr(config, "GGUF_MODEL_PATH", str(gguf))
    monkeypatch.setenv("GGUF_MODEL_PATH", str(gguf))
    monkeypatch.setattr(model_loader, "_preload_cuda_libs", lambda: None)
    monkeypatch.setattr(model_loader, "_load_transformers", lambda: pytest.fail("unexpected fallback"))

    def fail_load(**kwargs):
        raise ValueError("broken model")

    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(Llama=fail_load))
    with pytest.raises(RuntimeError, match="GGUF"):
        model_loader.load_model()
    assert model_loader.state.engine is None


def test_explicit_missing_gguf_does_not_autoselect(monkeypatch, tmp_path):
    (tmp_path / "other.gguf").touch()
    monkeypatch.setattr(config, "MODEL_ENGINE", "llama_cpp")
    monkeypatch.setattr(config, "GGUF_MODEL_PATH", str(tmp_path / "missing.gguf"))
    monkeypatch.setenv("GGUF_MODEL_PATH", str(tmp_path / "missing.gguf"))
    with pytest.raises(RuntimeError, match="GGUF"):
        model_loader.load_model()


@pytest.mark.parametrize("version,path", [("v4", "./checkpoint-250"), ("v1", "./checkpoint-v4")])
def test_bundled_adapter_version_mismatch(monkeypatch, version, path):
    monkeypatch.setattr(config, "PROMPT_VERSION", version)
    monkeypatch.setattr(config, "LORA_PATH", path)
    with pytest.raises(RuntimeError, match="không tương thích"):
        model_loader._load_transformers()


def test_lora_relative_path_resolved_from_service(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "PROMPT_VERSION", "v4")
    monkeypatch.setattr(config, "LORA_PATH", "custom/adapter")
    monkeypatch.chdir(tmp_path.parent)
    with pytest.raises(RuntimeError, match="LoRA checkpoint") as exc:
        model_loader._load_transformers()
    assert str(tmp_path / "custom" / "adapter") in str(exc.value)


# ---------------------------------------------------------------------------
# .env loading: sandbox project (không dùng .env thật của ai-service)
# ---------------------------------------------------------------------------

ENV_FILE_TEXT = """
MODEL_ENGINE=llama_cpp
PROMPT_VERSION=v2
LORA_PATH=./custom-lora
MAX_NEW_TOKENS=1200
GGUF_MODEL_PATH=./merged_model/model-v2.gguf
"""

CONFIG_DUMP_CODE = (
    "import json; from app.core import config as c; "
    "print(json.dumps([c.MODEL_ENGINE, c.PROMPT_VERSION, c.LORA_PATH, "
    "c.GGUF_MODEL_PATH, c.MAX_NEW_TOKENS]))"
)


def _cwd_dir(tmp_path):
    cwd = tmp_path / "run_from"
    cwd.mkdir()
    return cwd


def test_env_file_loaded_before_os_getenv(tmp_path):
    project = make_env_project(tmp_path, ENV_FILE_TEXT)
    result = run_cwd_isolated(project, _cwd_dir(tmp_path), CONFIG_DUMP_CODE)
    assert result.returncode == 0, result.stderr
    # Giá trị của .env được nạp trước os.getenv, neo vào project chứa config.py
    # dù cwd khác.
    assert json.loads(result.stdout) == ["llama_cpp", "v2", "./custom-lora",
                                         "./merged_model/model-v2.gguf", 1200]


def test_os_env_overrides_env_file(tmp_path):
    project = make_env_project(tmp_path, ENV_FILE_TEXT)
    # OS env phải ghi đè .env (override=False), các key còn lại lấy từ .env.
    result = run_cwd_isolated(project, _cwd_dir(tmp_path), CONFIG_DUMP_CODE,
                              MODEL_ENGINE="transformers", PROMPT_VERSION="v1")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["transformers", "v1", "./custom-lora",
                                         "./merged_model/model-v2.gguf", 1200]


@pytest.mark.parametrize("mode", ["missing", "existing"])
def test_env_gguf_path_reaches_loader_without_autoselect(tmp_path, mode):
    env_text = ENV_FILE_TEXT
    if mode == "missing":
        env_text = env_text.replace("model-v2.gguf", "missing.gguf")
    project = make_env_project(tmp_path, env_text)
    merged = project / "merged_model"
    merged.mkdir()
    cwd = _cwd_dir(tmp_path)
    if mode == "existing":
        # .env trỏ trực tiếp tới file này; stub ghi lại kwargs rồi lỗi,
        # nhờ đó biết loader nhận đúng explicit path mà không nạp model thật.
        (merged / "model-v2.gguf").touch()
        log = tmp_path / "stub_record.json"
    else:
        # Path từ .env thiếu; một decoy *.gguf cạnh đó không được autoselect thay.
        (merged / "other.gguf").touch()
        log = tmp_path / "stub_unused.json"
    (cwd / "llama_cpp.py").write_text(LLAMA_CPP_STUB)
    code = "from app.services import model_loader; model_loader.load_model()"
    result = run_cwd_isolated(project, cwd, code, extra_args=[str(log)])
    if mode == "existing":
        assert result.returncode != 0
        assert "GGUF" in result.stderr
        record = json.loads(log.read_text())
        assert record["model_path"] == str(merged / "model-v2.gguf")
    else:
        assert result.returncode != 0
        assert "Không tìm thấy file GGUF được chỉ định" in result.stderr
        assert not log.exists()  # stub chưa từng được dựng -> không có autoselect/load
