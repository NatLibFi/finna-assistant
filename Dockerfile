FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app
COPY app.py system_prompt.md .
RUN pip install --no-cache-dir gradio openai
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

CMD ["python", "-u", "app.py"]