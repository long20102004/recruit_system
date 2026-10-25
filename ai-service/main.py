import os
import json
import re
import time
import logging

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("AI-Service")


# ============================================================
# CONFIG
# ============================================================

BASE_MODEL_NAME = os.getenv(
    "BASE_MODEL_NAME",
    "unsloth/Qwen3-1.7B"
)

LORA_PATH = os.getenv(
    "LORA_PATH",
    "./checkpoint-250"
)


def _resolve(p: str) -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(_here, p))


def _adapter_base(lora_path: str) -> str | None:
    """Đọc base model thật từ adapter_config.json.

    Adapter train bằng Unsloth luôn ghi base ...-unsloth-bnb-4bit.
    Nạp đúng base này (strip suffix khi tải bản full) thì kích thước khớp
    và trọng số đúng; nạp sai base cùng kiến trúc thì chạy vẫn chạy nhưng
    output rác mà không báo lỗi.
    """
    cfg = os.path.join(_resolve(lora_path), "adapter_config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                name = json.load(f).get("base_model_name_or_path")
            if name:
                return name
        except Exception:
            pass
    return None

# GGUF merged của lần retrain mới nhất (ưu tiên số 1).
# File này là standalone (đã merge LoRA), adapter LoRA không cần thiết khi có nó.
GGUF_MODEL_PATH = os.getenv(
    "GGUF_MODEL_PATH",
    "./merged_model/model-qwen3-1.7b-q4_k_m.gguf"
)

MAX_NEW_TOKENS = int(
    os.getenv("MAX_NEW_TOKENS", "1500")
)

MAX_INPUT_TOKENS = int(
    os.getenv("MAX_INPUT_TOKENS", "8192")
)


# ============================================================
# GLOBAL MODEL
# ============================================================

engine = None     # "llama_cpp" (GGUF merged, ưu tiên) | "transformers" (base + LoRA)
llm = None        # llama_cpp instance khi engine == "llama_cpp"
tokenizer = None
model = None      # transformers PeftModel khi engine == "transformers"
gguf_path_used = None


# ============================================================
# REQUEST / RESPONSE
# ============================================================

class CVRequest(BaseModel):
    cv_text: str


class CVResponse(BaseModel):
    data: dict


# # ============================================================
# # SYSTEM PROMPT
# # ============================================================

# SYSTEM_PROMPT = """
# Bạn là hệ thống trích xuất thông tin CV.

# Nhiệm vụ:
# Đọc DUY NHẤT nội dung CV được cung cấp và trả về JSON.

# Đây là bài toán INFORMATION EXTRACTION.
# Không phải bài toán viết lại, tóm tắt hoặc suy luận.

# QUY TẮC:

# 1. NGUỒN DỮ LIỆU

# - Chỉ sử dụng thông tin xuất hiện trực tiếp trong CV.
# - Không sử dụng kiến thức bên ngoài.
# - Không sử dụng thông tin từ CV khác.
# - Không tự bịa thông tin.
# - Không suy đoán thông tin còn thiếu.

# 2. PERSONAL INFORMATION

# Thông tin ở phần header/contact của CV phải được đưa vào:

# personal_info.full_name
# personal_info.email
# personal_info.phone
# personal_info.github_url

# Nếu CV có các thông tin này thì phải lấy ra.

# 3. OBJECTIVE

# Lấy objective/career objective/profile nếu CV có.

# Không tự viết lại objective.

# 4. EDUCATION

# Lấy thông tin từ phần Education.

# Không tự suy đoán trường, ngành hoặc năm.

# 5. EXPERIENCE

# Chỉ lấy những mục thực sự thuộc phần Experience/Work Experience.

# Mỗi công ty/job là một experience.

# Không đưa project vào experience.

# 6. PROJECT

# Chỉ lấy những project thuộc phần Projects/Personal Projects.

# Mỗi project là một phần tử trong personal_projects.

# Không đưa experience vào project.

# 7. SKILLS

# Lấy các kỹ năng/công nghệ được liệt kê trong phần Skills/Technical Skills.

# Không bỏ qua skills.

# 8. PROJECT TECH STACK

# tech_stack của project chỉ chứa công nghệ được gắn với project đó.

# Không copy toàn bộ skills chung vào project.

# 9. ROLE

# Chỉ lấy role/job title nếu CV ghi rõ.

# Không tự suy luận role.

# 10. TEAM SIZE

# Chỉ lấy team_size nếu CV ghi rõ.

# 11. DATE

# Giữ nguyên thông tin ngày tháng như CV.

# Không tự thêm tháng/ngày nếu CV chỉ có năm.

# 12. URL

# Giữ URL nguyên dạng.

# Không tạo URL mới.

# 13. DESCRIPTION

# Không tự bịa hoặc thêm nội dung.

# Ưu tiên giữ nguyên nội dung CV.

# 14. OUTPUT

# Chỉ trả về JSON hợp lệ.

# Không Markdown.

# Không code block.

# Không giải thích.

# Không thêm field ngoài schema.
# """
# ============================================================
# SYSTEM PROMPT (ĐÃ LOẠI BỎ RÒ RỈ VÍ DỤ & KHÓA CHẶT EMPTY ARRAY)
# ============================================================

SYSTEM_PROMPT = """
Bạn là hệ thống trích xuất thông tin CV.

Nhiệm vụ:
Đọc DUY NHẤT nội dung CV được cung cấp và trả về JSON theo đúng schema.
Đây là bài toán INFORMATION EXTRACTION. Chỉ lấy thông tin CÓ SẴN trong CV. Tuyệt đối KHÔNG tự bịa.

QUY TẮC RÀNG BUỘC THEO TỪNG TRƯỜNG:

1. PERSONAL INFORMATION
Trích xuất: full_name, email, phone, github_url dạng chuỗi thô (raw string).

2. OBJECTIVE & EDUCATION
- objective: Lấy nguyên văn mục tiêu nghề nghiệp nếu có, không có để null.
- education: Trích xuất school, major, start_year, end_year, gpa.

3. EXPERIENCE & PROJECTS
- experience: Chỉ chứa các công ty/tổ chức làm việc thực tế.
- personal_projects: Chỉ chứa dự án cá nhân hoặc đồ án.
  + Mỗi project CHỈ gồm các key: name, role, team_size, start_date, end_date, github_url, description, tech_stack.
  + TUYỆT ĐỐI KHÔNG tự tạo key mới (như role_description, team_description). Gom toàn bộ nội dung mô tả vào key "description".
  + description: Tóm tắt 2-3 ý ngắn gọn cốt lõi, không chép đoạn văn quá dài dòng.

4. PHÂN BIỆT HONOURS vs CERTIFICATES vs LANGUAGES (RẤT QUAN TRỌNG):

- "honours" (Giải thưởng, Học bổng, Thành tích):
  + Chứa toàn bộ học bổng (Scholarship, Học bổng đầu vào, Học bổng khuyến khích...).
  + Chứa các giải thưởng cuộc thi hoặc danh hiệu học tập/công việc.
  + NẾU CV KHÔNG CÓ THÀNH TÍCH/HỌC BỔNG: BẮT BUỘC ĐỂ MẢNG RỖNG [].

- "certificates" (Chứng chỉ nghề nghiệp / kỹ thuật):
  + CHỈ trích xuất các chứng chỉ nghề nghiệp/khóa học được ghi TRỰC TIẾP trong CV.
  + KHÔNG đưa học bổng vào certificates.
  + KHÔNG đưa điểm thi ngoại ngữ vào certificates.
  + NẾU CV KHÔNG CÓ MỤC CHỨNG CHỈ HOẶC KHÔNG CÓ CHỨNG CHỈ NÀO: BẮT BUỘC TRẢ VỀ MẢNG RỖNG []. TUYỆT ĐỐI KHÔNG TỰ BỊA RA BẤT KỲ CHỨNG CHỈ NÀO.

- "languages" (Ngoại ngữ):
  + Chứa tên ngôn ngữ ("language") và điểm số/trình độ ("note").
  + Điểm số ngoại ngữ đã vào languages thì KHÔNG đưa vào honours hoặc certificates.
  + NẾU CV KHÔNG CÓ NGOẠI NGỮ: BẮT BUỘC ĐỂ MẢNG RỖNG [].

5. SKILLS & TECH STACK
- skills: Kỹ năng chung liệt kê trong CV.
- tech_stack: Chỉ công nghệ của riêng từng dự án.

6. ĐỊNH DẠNG ĐẦU RA
Chỉ trả về DUY NHẤT một JSON hợp lệ. Không Markdown, không code fences, không giải thích nội dung.
"""

# ============================================================
# JSON SCHEMA
# ============================================================

JSON_SCHEMA = """
Schema:

{
  "personal_info": {
    "full_name": null,
    "email": null,
    "phone": null,
    "github_url": null
  },

  "objective": null,

  "education": [],

  "experience": [],

  "personal_projects": [],

  "skills": [],

  "certificates": [],

  "honours": [],

  "languages": []
}

Cấu trúc từng phần tử khi CÓ dữ liệu trong CV:
- education item: {"school": str, "major": str, "start_year": str/int, "end_year": str/int, "gpa": str}
- experience item: {"company": str, "job_title": str, "start_date": str, "end_date": str, "description": [str]}
- personal_projects item: {"name": str, "role": str, "team_size": int, "start_date": str, "end_date": str, "github_url": str, "description": [str], "tech_stack": [str]}
- languages item: {"language": str, "note": str}
"""
JSON_SCHEMA_FORMAT = JSON_SCHEMA


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_cv_text(text: str) -> str:

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Chỉ loại bỏ dòng trống quá nhiều.
    # Không normalize toàn bộ khoảng trắng vì layout CV có thể quan trọng.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    global tokenizer
    global model
    global engine
    global llm
    global gguf_path_used

    logger.info("=" * 70)
    logger.info("Loading CV Extraction Model")
    logger.info("=" * 70)

    # --------------------------------------------------------
    # Ưu tiên 1: GGUF merged (bản retrain mới nhất, standalone)
    # --------------------------------------------------------
    _here = os.path.dirname(os.path.abspath(__file__))
    _gguf = (
        GGUF_MODEL_PATH
        if os.path.isabs(GGUF_MODEL_PATH)
        else os.path.normpath(os.path.join(_here, GGUF_MODEL_PATH))
    )
    if os.path.exists(_gguf):
        try:
            # Tự động preload libcudart/libcublas nếu chạy trên môi trường Linux/CUDA (Google Colab)
            try:
                import ctypes
                import glob
                _cuda_dirs = [
                    "/usr/local/cuda/lib64",
                    "/usr/local/cuda-12/lib64",
                    "/usr/local/cuda-12.4/lib64",
                    "/usr/local/cuda-12.2/lib64",
                    "/usr/local/cuda-12.1/lib64",
                    "/usr/local/cuda-12.0/lib64",
                    "/usr/lib/x86_64-linux-gnu",
                ]
                try:
                    import site
                    for _sp in site.getsitepackages():
                        _cuda_dirs.extend(glob.glob(os.path.join(_sp, "nvidia", "*", "lib")))
                except Exception:
                    pass
                for _d in _cuda_dirs:
                    if os.path.isdir(_d):
                        for _lib in ["libcudart.so.12", "libcudart.so", "libcublas.so.12", "libcublas.so"]:
                            _p = os.path.join(_d, _lib)
                            if os.path.exists(_p):
                                try:
                                    ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                                except Exception:
                                    pass
            except Exception as _ce:
                logger.debug(f"Preload CUDA libs note: {_ce}")

            from llama_cpp import Llama

            logger.info(f"GGUF found: {_gguf}")
            logger.info("Loading GGUF (merged finetune, LoRA adapter KHÔNG cần thiết)...")
            llm = Llama(
                model_path=_gguf,
                n_ctx=4096,
                n_threads=6,
                n_gpu_layers=99,      # Offload 100% layers lên GPU
                verbose=True
            )
            engine = "llama_cpp"
            gguf_path_used = _gguf
            logger.info("=" * 70)
            logger.info("MODEL LOADED SUCCESSFULLY (llama.cpp GGUF)")
            logger.info("=" * 70)
            return
        except Exception:
            logger.exception("Nạp GGUF thất bại, fallback sang transformers...")

    # --------------------------------------------------------
    # Ưu tiên 2: transformers base + LoRA (fallback, chậm hơn ~5 lần)
    # Adapter checkpoint-250/ là bản retrain mới (Qwen3-1.7B), cùng bản với
    # file GGUF — chỉ khác đường nạp (transformers fp32 thay vì llama.cpp Q4).
    # --------------------------------------------------------
    lora_abs = _resolve(LORA_PATH)
    base_from_adapter = _adapter_base(LORA_PATH)
    base_name = BASE_MODEL_NAME
    if base_from_adapter and base_from_adapter != BASE_MODEL_NAME:
        logger.info(
            f"Adapter khai base '{base_from_adapter}' -> "
            f"dùng đúng base này thay vì default '{BASE_MODEL_NAME}'."
        )
        base_name = base_from_adapter
    # Strip suffix unsloth-bnb-4bit để tải bản full-precision
    base_name = base_name.replace("-unsloth-bnb-4bit", "").replace("-unsloth", "")

    logger.info(f"Base model : {base_name}")
    logger.info(f"LoRA path  : {lora_abs}")

    if not os.path.exists(lora_abs):

        raise RuntimeError(
            f"Không tìm thấy LoRA checkpoint: {lora_abs}"
        )

    # --------------------------------------------------------
    # DEVICE
    # --------------------------------------------------------

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    dtype = (
        torch.float16
        if device == "cuda"
        else torch.float32
    )

    logger.info(f"Device : {device}")
    logger.info(f"Dtype  : {dtype}")

    # --------------------------------------------------------
    # TOKENIZER
    # --------------------------------------------------------

    logger.info("Loading tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        lora_abs,
        use_fast=True
    )

    # --------------------------------------------------------
    # BASE MODEL
    # --------------------------------------------------------

    logger.info("Loading base model...")

    base_model = AutoModelForCausalLM.from_pretrained(
        base_name,
        torch_dtype=dtype,
        low_cpu_mem_usage=True
    )

    # --------------------------------------------------------
    # LORA
    # --------------------------------------------------------

    logger.info("Loading LoRA adapter...")

    model = PeftModel.from_pretrained(
        base_model,
        lora_abs
    )

    model.to(device)

    model.eval()

    engine = "transformers"

    logger.info("=" * 70)
    logger.info("MODEL LOADED SUCCESSFULLY (transformers + LoRA)")
    logger.info("=" * 70)


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt_gguf(cv_text: str) -> str:
    # 1. Dựng Prompt với thẻ think đóng sẵn và mớm ký tự '{'
    prompt = f"""<|im_start|>system
{SYSTEM_PROMPT}

{JSON_SCHEMA_FORMAT}
<|im_end|>
<|im_start|>user
{cv_text}<|im_end|>
<|im_start|>assistant
<think>

</think>
{{"""
    return prompt


def build_prompt(cv_text: str):
    # Dùng chung prompt với build_prompt_gguf để đóng sẵn thẻ think và mớm '{'
    return build_prompt_gguf(cv_text)


# ============================================================
# GENERATE
# ============================================================

def generate_cv(cv_text: str):

    # Đường GGUF (llama.cpp): model retrain mới nhất
    if engine == "llama_cpp":
        prompt = build_prompt_gguf(cv_text)
        logger.info("Inference bằng llama.cpp (GGUF)...")
        start = time.time()
        resp = llm(
            prompt=prompt,
            max_tokens=MAX_NEW_TOKENS,          # Tăng nhẹ lên 1500 để không bao giờ bị cụt
            temperature=0.0,
            repeat_penalty=1.0,
            stop=["<|im_end|>", "<|endoftext|>", "</think>"],  # BẮT BUỘC: Ngắt ngay khi gặp </think>
        )
        duration = time.time() - start
        raw_output = resp["choices"][0]["text"].strip()
        usage = resp.get("usage", {})
        logger.info(
            f"Input tokens: {usage.get('prompt_tokens', '?')}"
        )
        logger.info(
            f"Output tokens: {usage.get('completion_tokens', '?')}"
        )
        logger.info(
            f"Inference time: {duration:.2f}s"
        )
        logger.info(
            f"Raw output length: {len(raw_output)} chars"
        )

        # Vì ta đã mớm ký tự '{' ở cuối prompt, cần ghép lại vào đầu text nếu nó chưa có
        if not raw_output.startswith("{"):
            raw_output = "{\n" + raw_output

        return raw_output

    # Đường Transformers (khi fallback hoặc chạy trực tiếp LoRA trên GPU)
    prompt = build_prompt(cv_text)

    device = next(
        model.parameters()
    ).device

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

    logger.info(
        f"Input tokens: {input_tokens}"
    )

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

    # Chỉ lấy phần model generate
    generated_tokens = outputs[
        0
    ][input_tokens:]

    output_tokens = len(
        generated_tokens
    )

    raw_output = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    ).strip()

    # Vì ta đã mớm ký tự '{' ở cuối prompt, cần ghép lại vào đầu text nếu nó chưa có
    if not raw_output.startswith("{"):
        raw_output = "{\n" + raw_output

    logger.info(
        f"Output tokens: {output_tokens}"
    )

    logger.info(
        f"Inference time: {duration:.2f}s"
    )

    logger.info(
        f"Raw output length: {len(raw_output)} chars"
    )

    return raw_output


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(text: str) -> dict:
    # 1. Nếu có thẻ </think>, cắt bỏ toàn bộ phần rác phía sau nó
    if "</think>" in text:
        text = text.split("</think>")[0].strip()

    # 2. Xóa các markdown block ```json ... ```
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # 3. Thử parse trực tiếp
    try:
        return json.loads(text)
    except Exception:
        pass

    # 4. Tìm khối { ... } đầu tiên hợp lệ nhất
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 5. Fallback qua json_repair nếu có thư viện
    try:
        import json_repair
        return json_repair.loads(text)
    except Exception:
        pass

    raise ValueError("Model không trả về JSON hợp lệ")


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="CV Extraction AI Service"
)


@app.on_event("startup")
def startup():

    load_model()


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    if engine is None:

        raise HTTPException(
            status_code=503,
            detail="Model chưa được load"
        )

    info = {"status": "ok", "engine": engine}
    if engine == "llama_cpp":
        info["model"] = gguf_path_used
    else:
        info["model"] = BASE_MODEL_NAME
        info["lora"] = LORA_PATH
        info["device"] = str(
            next(model.parameters()).device
        )
    return info


# ============================================================
# EXTRACT CV
# ============================================================

@app.post(
    "/api/v1/extract-cv",
    response_model=CVResponse
)
def extract_cv(request: CVRequest):

    if engine is None:

        raise HTTPException(
            status_code=503,
            detail="Model chưa được load"
        )

    if not request.cv_text.strip():

        raise HTTPException(
            status_code=400,
            detail="cv_text không được rỗng"
        )

    cv_text = clean_cv_text(
        request.cv_text
    )

    logger.info(
        f"CV length: {len(cv_text)} chars"
    )

    try:

        raw_output = generate_cv(
            cv_text
        )

        logger.info(
            "Raw model output:"
        )

        logger.info(
            raw_output
        )

        data = extract_json(
            raw_output
        )

        return {
            "data": data
        }

    except Exception as e:

        logger.exception(
            "CV extraction failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )