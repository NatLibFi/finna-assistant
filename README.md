# finna-assistant

Finna assistant is a GPT-based chatbot interface that enables searching library, museum and archival records using the Finna search service.

## Installation

### Running with Python

#### Install dependencies

    pip install -r requirements.txt

#### Set environment variables

The application requires that the environment variable `AZURE_OPENAI_KEY` is set.

#### Start the application

    python app.py

The app will be available at http://127.0.0.1:7860. You can customize the port or host with the `GRADIO_SERVER_PORT` and `GRADIO_SERVER_NAME` environment variables.

### Running with Docker

#### Build the Docker image

    docker build -t finna-assistant .

#### Run the container

    docker run -p 7860:7860 -e AZURE_OPENAI_KEY=<openai-key> finna-assistant

## Run tests

Run the following command in the root of the project:

    python tests/tests.py

## Generate embeddings files

Run the following command at the root of the project:

    python scripts/generate_embeddings.py

This will regenerate the embeddings .pkl files in the `embeddings` folder based on the CSV files in the `data` folder. The script should be run whenever the files in the data folder are modified.