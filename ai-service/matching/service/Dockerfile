# cvmatch-ai: API match CV <-> JD (I01). Build tu thu muc ai-service/matching/service:
#   docker build -t cvmatch-ai ai-service/matching/service                                  # CPU
#   docker build -t cvmatch-ai --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu130 ai-service/matching/service   # GPU
# Model bge-m3 KHONG nam trong image: tai lan dau vao HF_HOME (gan volume de khong tai lai).
FROM python:3.11-slim

ARG TORCH_VERSION=2.14.0
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface \
    CVMATCH_ENV=prod \
    CVMATCH_DEVICE=cpu \
    CVMATCH_KB_DIR=/kb \
    CVMATCH_PORT=8000

WORKDIR /app

RUN pip install --index-url ${TORCH_INDEX} torch==${TORCH_VERSION}
COPY docker/requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install -r /tmp/requirements.lock.txt

# config/ va migrations/ duoc doc theo duong dan tuong doi voi src/ -> cai editable trong /app
COPY pyproject.toml README.md ./
COPY config ./config
COPY migrations ./migrations
COPY src ./src
RUN pip install --no-deps -e .

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=10s --start-period=600s --retries=10 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('CVMATCH_PORT','8000'), timeout=5)"

CMD ["cvmatch", "api", "prod"]
