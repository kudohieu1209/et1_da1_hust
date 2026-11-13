FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM python:3.12-slim AS runtime
ENV HOME=/home/user \
    PORT=7860 \
    COOKIE_SECURE=true \
    PYTHONUNBUFFERED=1 \
    PYTHON_DOTENV_DISABLED=1 \
    RAG_SYNC_ON_STARTUP=auto \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    ANONYMIZED_TELEMETRY=False \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    MALLOC_TRIM_THRESHOLD_=131072 \
    VECTOR_DB_DIR=/home/user/app/data/vector_db

# ONNX Runtime's Linux wheel links against libstdc++.so.6.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 user
WORKDIR /home/user/app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user:user backend/app/ backend/app/
COPY --chown=user:user backend/scripts/build_vector_db.py backend/scripts/build_vector_db.py
COPY --chown=user:user data/processed/curricula/ data/processed/curricula/
COPY --chown=user:user data/processed/curriculum_approvals.json data/processed/curriculum_approvals.json
COPY --chown=user:user data/documents/ data/documents/
COPY --chown=user:user data/raw/ctt_et_conditions.json data/raw/ctt_et_conditions.json
COPY --chown=user:user data/raw/hust_undergraduate_programs.json data/raw/hust_undergraduate_programs.json
COPY --chown=user:user data/raw/hust_program_curriculum_sources.json data/raw/hust_program_curriculum_sources.json
COPY --chown=user:user data/raw/hust_curriculum_candidates.json data/raw/hust_curriculum_candidates.json
COPY --chown=user:user data/raw/official_curricula/ data/raw/official_curricula/
COPY --chown=user:user data/raw/reviewed_curricula/ data/raw/reviewed_curricula/
COPY --from=frontend-build --chown=user:user /build/frontend/dist/ frontend/dist/
RUN mkdir -p "$VECTOR_DB_DIR" "$HOME/.cache/chroma" \
    && chown -R user:user /home/user/app /home/user/.cache

USER user
WORKDIR /home/user/app/backend
# Running as the runtime user keeps both Chroma and its downloaded ONNX cache writable.
RUN python scripts/build_vector_db.py
EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
