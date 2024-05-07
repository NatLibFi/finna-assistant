FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app
COPY app.py .
RUN pip install --no-cache-dir gradio openai finna_client
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

CMD ["python", "-u", "app.py"]