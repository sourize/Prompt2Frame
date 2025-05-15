# Prompt2Frame Backend

This is the backend service for the Prompt2Frame application, which generates mathematical animations using Manim.

## Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── app.py              # Flask application
│   ├── generator.py        # Manim code generation using Groq
│   ├── executor.py         # Manim code execution
│   └── gunicorn_config.py  # Gunicorn server configuration
└── requirements.txt        # Python dependencies
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
FLASK_APP=src/app.py
FLASK_ENV=production
GROQ_API_KEY=your_groq_api_key
```

## Running the Server

Development:
```bash
flask run
```

Production:
```bash
gunicorn src.app:app --config src/gunicorn_config.py
```

## API Endpoints

- `POST /generate`: Generate animation from text prompt
- `GET /media/videos/<filename>`: Serve generated videos
- `GET /health`: Health check endpoint 