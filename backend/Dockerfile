FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/opt/models TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-runtime.txt
# Download at build time so query handling does not depend on model-hub access.
RUN python -c "from sentence_transformers import SentenceTransformer,CrossEncoder; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
COPY --chown=10001:10001 . .
# Cached model files are readable without rewriting their large build layer.
RUN useradd --uid 10001 --create-home neoguard
USER 10001
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
