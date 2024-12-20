FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app
COPY app.py requirements.txt .
COPY data/ data/
COPY prompts/ prompts/
COPY scripts/ scripts/
COPY static/ static/

RUN pip install --no-cache-dir -r requirements.txt

ARG AZURE_OPENAI_KEY
ENV AZURE_OPENAI_KEY=${AZURE_OPENAI_KEY}

RUN python scripts/generate_embeddings.py

EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

RUN (date -u +"%Y-%m-%d %H:%M:%S" --date='2 hours') > date.txt

CMD ["python", "-u", "app.py"]