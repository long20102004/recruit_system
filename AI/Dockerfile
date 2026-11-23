FROM python:3.11-slim
WORKDIR /app
COPY requirements-fast.txt requirements-interview.txt ./
# CPU wheels avoid pulling CUDA dependencies onto a CPU deployment.
RUN pip install --no-cache-dir 'torch>=2.2,<3' --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-interview.txt
COPY src ./src
COPY data ./data
ENV HIRELENS_MODE=bertscore HIRELENS_DEVICE=cpu HIRELENS_THREADS=2 HIRELENS_BATCH_SIZE=4
EXPOSE 8000
CMD ["python", "-m", "src.bootstrap"]
