# Prompt2Frame 🎬

Transform text descriptions into beautiful animations using AI and Manim. This project combines the power of Large Language Models with Manim's mathematical animation capabilities to create stunning visualizations from natural language descriptions.

## 🌟 Features

- **Text-to-Animation**: Convert natural language descriptions into animated scenes using Manim
- **Real-time Generation**: Watch your animations come to life with instant feedback
- **Modern UI**: Clean and intuitive user interface built with Vite, React, and Tailwind CSS
- **Responsive Design**: Works seamlessly on both desktop and mobile devices
- **Flexible Deployment**: Choose between single-service or microservices architecture
- **Docker Support**: Containerized deployment for easy setup and scaling
- **Production Ready**: Configured with Uvicorn for robust production deployment
- **API Documentation**: Interactive API docs with Swagger UI

## 🌐 Live Demo

Visit [Prompt2Frame](https://prompt2frame.sourish.xyz) to try it out!

## 🏗️ Project Structure

The project supports two deployment architectures:

### Option 1: Single Service (Recommended for Local Development)
```
prompt2frame/
├── backend/                 # Complete backend service
│   ├── src/                # Core backend logic
│   │   ├── main.py        # FastAPI application
│   │   ├── executor.py    # Manim execution logic
│   │   ├── generator.py   # Animation generation
│   │   ├── prompt_expander.py # LLM prompt processing
│   │   └── gunicorn_config.py # Production server config
│   └── requirements.txt   # Python dependencies
├── frontend/              # React frontend application
│   ├── src/             # Frontend source code
│   ├── public/          # Static assets
│   └── package.json     # Node.js dependencies
└── Dockerfile           # Container configuration
```

### Option 2: Split Services (For Render Free Tier)
```
prompt2frame/
├── manimllmservice/        # LLM Service
│   ├── main.py           # FastAPI LLM service
│   ├── prompt_expander.py # LLM prompt processing
│   ├── generator.py      # Animation code generation
│   └── requirements.txt  # Service dependencies
├── manim-renderer-service/ # Manim Rendering Service
│   ├── main.py          # FastAPI rendering service
│   ├── executor.py      # Manim execution logic
│   └── requirements.txt # Service dependencies
├── frontend/              # React frontend application
│   ├── src/             # Frontend source code
│   ├── public/          # Static assets
│   └── package.json     # Node.js dependencies
└── Dockerfile           # Container configuration
```

## 🏛️ Architecture

The project follows a microservices architecture with three main services:

1. **Main Backend (API Gateway)**
   - Handles client requests
   - Routes requests to appropriate services
   - Manages authentication and rate limiting

2. **LLM Service (manimllmservice)**
   - Processes natural language prompts
   - Generates Manim code using Groq LLM
   - Handles prompt expansion and optimization

3. **Manim Renderer Service (manim-renderer-service)**
   - Executes Manim code
   - Handles video rendering
   - Manages animation output

## 🛠️ Tech Stack

### Backend Services
- **FastAPI**: Modern, fast web framework for building APIs with Python
- **Manim**: Mathematical animation engine for creating animations
- **Groq**: LLM API for code generation and prompt expansion
- **Uvicorn**: ASGI server for production deployment
- **Docker**: Containerization for consistent deployment

### Frontend
- **Vite**: Next-generation frontend tooling
- **React**: UI library for building interactive interfaces
- **Tailwind CSS**: Utility-first CSS framework
- **TypeScript**: Type-safe JavaScript
- **Axios**: HTTP client for API communication

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- FFmpeg (required for Manim)
- Docker (optional, for containerized deployment)

## 🚀 Getting Started

### Option 1: Single Service Setup (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/sourize/prompt2frame.git
   cd prompt2frame
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the backend directory with:
   ```
   GROQ_API_KEY=your_groq_api_key
   DEBUG=false
   PORT=5000
   ```

5. Run the backend server:
   ```bash
   uvicorn src.main:app --reload --port 5000
   ```

### Option 2: Split Services Setup (For Render)

1. Clone the repository:
   ```bash
   git clone https://github.com/sourize/prompt2frame.git
   cd prompt2frame
   ```

2. Create and activate virtual environments for each service:
   ```bash
   # For LLM service
   python -m venv manimllmservice/myenv
   source manimllmservice/myenv/bin/activate
   
   # For Manim renderer service
   python -m venv manim-renderer-service/myenv
   source manim-renderer-service/myenv/bin/activate
   ```

3. Install dependencies for each service:
   ```bash
   # LLM service
   cd manimllmservice
   pip install -r requirements.txt
   
   # Manim renderer service
   cd ../manim-renderer-service
   pip install -r requirements.txt
   ```

4. Set up environment variables for each service:
   ```
   # manimllmservice/.env
   GROQ_API_KEY=your_groq_api_key
   PORT=5001
   
   # manim-renderer-service/.env
   PORT=5002
   ```

5. Run each service:
   ```bash
   # Terminal 1 - LLM service
   cd manimllmservice
   uvicorn main:app --reload --port 5001
   
   # Terminal 2 - Manim renderer service
   cd manim-renderer-service
   uvicorn main:app --reload --port 5002
   ```

### Frontend Setup (Same for both options)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

3. Run the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Docker Deployment

#### Option 1: Single Service
```bash
cd backend
docker build -t prompt2frame-backend .
docker run -p 5000:5000 prompt2frame-backend
```

#### Option 2: Split Services
```bash
# Build all services
docker-compose build

# Run all services
docker-compose up
```

## 🎯 Usage

1. Enter a text description of the animation you want to create
2. Click "Generate Animation"
3. Wait for the animation to be generated (may take a few moments)
4. Watch your animation!

### Example Prompts

- "A blue ball bouncing with a scaling shadow"
- "A rotating cube with changing colors"
- "A sine wave that transforms into a circle"
- "A particle system with gravity"

## ⚠️ Important Notes

- The services may take a minute to wake up after inactivity
- If you encounter an error, try refreshing the browser
- The current version uses Groq's LLM, so animations might not be exact matches to the prompts
- Ensure FFmpeg is properly installed for Manim to work correctly
- For local development, the single service option (Option 1) is recommended
- The split services option (Option 2) is specifically designed for Render's free tier deployment

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details.

## 👨‍💻 Author

- **Sourish** - [Portfolio](https://sourish.xyz)|[𝕏](https://x.com/sourize_)

## 🙏 Acknowledgments

- [Manim](https://github.com/ManimCommunity/manim) for the animation engine
- [Groq](https://groq.com) for the LLM API
- [FastAPI](https://fastapi.tiangolo.com) for the backend framework
- [Vite](https://vitejs.dev) for the frontend build tool
- [Tailwind CSS](https://tailwindcss.com) for the styling

## 📞 Support

If you encounter any issues or have questions, please open an issue in the GitHub repository.

---

Made with ❤️ by Sourish