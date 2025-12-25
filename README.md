# Prompt2Frame 🎬✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![Manim](https://img.shields.io/badge/Engine-Manim-ecec4f?style=flat&logo=python&logoColor=black)](https://github.com/ManimCommunity/manim)
[![Groq](https://img.shields.io/badge/AI-Groq-f55036?style=flat&logo=groq&logoColor=white)](https://groq.com)

**Prompt2Frame** is an AI-powered animation generator that transforms natural language descriptions into stunning, mathematical 2D animations. It leverages the power of Large Language Models (LLM) and the Manim engine to bring your ideas to life instantly.

---

## 🚀 Key Features

### 🎨 **AI-Driven Creativity**
- **Text-to-Animation**: Just describe what you want (e.g., "A red circle morphing into a blue square"), and watch it happen.
- **Smart Prompt Expansion**: Vague ideas are automatically expanded into detailed, technically accurate animation scripts.
- **Code Generation**: Uses Groq's high-speed LLMs (Llama 3) to generate error-free Manim Python code.

### ⚡ **High Performance**
- **Smart Caching**: 
  - **Instant Replay**: Caches generated videos (7-day TTL) for sub-second responses to duplicate requests.
  - **Prompt Cache**: Caches expanded prompts (24h TTL) to save API costs and time.
- **Optimized Rendering**: Parallel video processing and efficient ffmpeg concatenation.

### 🛡️ **Enterprise-Grade Security**
- **Rate Limiting**: Sliding window protection (5 requests/min per IP) to prevent abuse.
- **Input Sanitization**: Extensive validation to block malicious code injection and dangerous patterns.
- **Circuit Breaker**: Automatic failover and recovery for external API dependencies.
- **Secure CORS**: Strictly configured cross-origin policies for production safety.

### 📱 **Modern UI/UX**
- **Responsive Design**: Fully adaptive interface that works beautifully on mobile, tablet, and desktop.
- **Dark Mode**: Sleek, glassmorphic dark theme designed for visual comfort.
- **Interactive Player**: Integrated video player with instant download and replay capabilities.

---

## 🏗️ Architecture

Prompt2Frame uses a robust monolithic architecture suitable for both local development and scalable cloud deployment.

```
prompt2frame/
├── backend/                 # FastAPI Service
│   ├── src/                 # Core Logic
│   │   ├── app.py           # API Gateway & Middleware
│   │   ├── generator.py     # AI Code Generation
│   │   ├── executor.py      # Manim Rendering Engine
│   │   ├── cache.py         # Caching System
│   │   └── rate_limiter.py  # Security & Throttling
│   └── media/               # Generated Video Storage
│
├── frontend/                # React Application
│   ├── src/                 # UI Components & Logic
│   └── public/              # Static Assets
│
└── requirements.txt         # Dependencies
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Manim Community v0.17+, Groq SDK
- **Frontend**: React 18, Vite, Tailwind CSS, Framer Motion, Lucide Icons, Shadcn UI
- **Infrastructure**: Docker support (coming soon), Multi-environment configuration (.env)

---

## 🚦 Getting Started

### Prerequisites
- **Python 3.10+** (Required for Manim)
- **Node.js 18+** & npm
- **FFmpeg** (Must be installed and in system PATH)
- **Groq API Key** (Get one for free at [console.groq.com](https://console.groq.com))

### 1. Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/sourize/prompt2frame.git
cd prompt2frame/backend

# 2. Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Environment
# Create a .env file in /backend and add:
GROQ_API_KEY=your_groq_api_key_here
PORT=5000
DEBUG=true
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:8080"]
```

### 2. Frontend Setup

```bash
# 1. Go to frontend directory
cd ../frontend

# 2. Install dependencies
npm install

# 3. Configure Environment
# Create a .env file in /frontend and add:
VITE_BACKEND_URL=http://localhost:5000

# 4. Start Development Server
npm run dev
```

### 3. Run the Backend
```bash
# From /backend directory
python -m uvicorn src.app:app --reload --port 5000
```

Visit `http://localhost:5173` (or the port shown in your terminal) to start creating!

---

## 🧪 Testing & Verification

We include built-in health checks and validation tools.

- **Health Check**: `GET /health` - Verifies API status and dependency availability.
- **Metrics**: `GET /metrics` - View cache hit rates, request counts, and system load.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Sourish**
- 🌐 [Portfolio](https://sourish.xyz)
- 𝕏 [Twitter/X](https://x.com/sourize_)

---

Made with ❤️ and 🤖 using Prompt2Frame