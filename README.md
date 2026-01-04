# Prompt2Frame 🎬✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![Manim](https://img.shields.io/badge/Engine-Manim-ecec4f?style=flat&logo=python&logoColor=black)](https://github.com/ManimCommunity/manim)
[![Groq](https://img.shields.io/badge/AI-Groq-f55036?style=flat&logo=groq&logoColor=white)](https://groq.com)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat&logo=vercel&logoColor=white)](https://vercel.com)

**Prompt2Frame** is an AI-powered animation generator that transforms natural language descriptions into stunning, mathematical 2D animations. It leverages the power of Large Language Models (LLM) and the Manim engine to bring your ideas to life instantly.

---

## 🚀 Key Features

### 🎨 **AI-Driven Creativity**
- **Text-to-Animation**: Just describe what you want (e.g., "A red circle morphing into a blue square"), and watch it happen.
- **Smart Prompt Expansion**: Vague ideas are automatically expanded into detailed, technically accurate animation scripts.
- **Code Generation**: Uses Groq's high-speed LLMs (Llama 3) to generate error-free Manim Python code.

### ⚡ **High Performance & Security**
- **Smart Caching**: 
  - **Instant Replay**: Caches generated videos (7-day TTL) for sub-second responses to duplicate requests.
  - **Prompt Cache**: Caches expanded prompts (24h TTL) to save API costs and time.
- **Secure Proxy**: Built-in Vercel Serverless Proxy (`api/generate.js`) to securely communicate with private backends without exposing tokens.
- **Enhanced Safety**:
  - **Anti-Overlap Logic**: Smart prompting ensures text doesn't overlap with shapes.
  - **Input Sanitization**: Extensive validation to block malicious code.

### 📱 **Modern UI/UX**
- **Professional Design**: Engineering-focused aesthetic with serif typography and grid patterns.
- **Responsive Interface**: Works beautifully on mobile with optimized footer and controls.
- **Interactive Player**: Integrated video player with download capabilities.

---

## 🏗️ Architecture

Prompt2Frame uses a separated frontend-backend architecture with a secure proxy layer for deployment.

```
prompt2frame/
├── backend/                 # FastAPI Service (Private/Hugging Face)
│   ├── src/                 # Core Logic (App, Generator, Executor)
│   └── media/               # Generated Video Storage
│
├── frontend/                # React Application (Vercel)
│   ├── api/                 # Serverless Proxies
│   │   ├── generate.js      # Securely adds HF_TOKEN to requests
│   │   └── media.js         # Proxies video streams securely
│   └── src/                 # UI Components (Header, SearchInterface)
│
└── requirements.txt         # Backend Dependencies
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, Manim Community v0.17+, Groq SDK
- **Frontend**: React 18, Vite, Tailwind CSS, Framer Motion
- **Deployment**: Vercel (Frontend + Proxy), Hugging Face Spaces (Backend)

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

# 4. Configure Environment (.env)
GROQ_API_KEY=your_groq_api_key_here
PORT=5000
DEBUG=true
```

### 2. Frontend Setup

```bash
# 1. Go to frontend directory
cd ../frontend

# 2. Install dependencies
npm install

# 3. Configure Environment (.env)
# Point to your local backend OR Vercel proxy location
VITE_BACKEND_URL=http://localhost:5000 
# Note: For production features like Private HF Access, deploy to Vercel.

# 4. Start Development Server
npm run dev
```

### 3. Deploying to Vercel (Secure Private Access)

If you are using a Private Hugging Face Space for the backend, you must configure your Vercel project Environment Variables:

| Variable | Description |
| :--- | :--- |
| `VITE_BACKEND_URL` | URL of your backend (e.g., `https://your-space.hf.space`) |
| `HF_TOKEN` | Your Private Hugging Face Access Token |

The included `api/` proxy functions will automatically attach this token to requests, keeping it safe from the client-side.

---

## 🧪 Testing & Validation

- **Health Check**: `GET /health` - Verifies API status.
- **Constraints**: The UI includes notifications about free-tier limitations (concurrency, timeouts) to manage user expectations.

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
- 🌐 [Portfolio](https://sourish.me)
- 𝕏 [Twitter/X](https://x.com/sourize_)

---

Made with ❤️ and 🤖 using Prompt2Frame