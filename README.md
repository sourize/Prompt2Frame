# Prompt2Frame 🎬

Transform text descriptions into beautiful animations using AI and Manim.

## 🌟 Features

- **Text-to-Animation**: Convert natural language descriptions into animated scenes
- **Real-time Generation**: Watch your animations come to life instantly
- **Modern UI**: Clean and intuitive user interface built with Next.js and Tailwind CSS
- **Responsive Design**: Works seamlessly on both desktop and mobile devices

## 🌐 Live Demo

Visit [Prompt2Frame](https://prompt2frame.vercel.com) to try it out!

## 🛠️ Tech Stack

### Backend
- **Flask**: Python web framework
- **Manim**: Mathematical animation engine
- **Groq**: LLM API for code generation
- **Gunicorn**: Production server

### Frontend
- **Next.js**: React framework
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animation library
- **Axios**: HTTP client

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- FFmpeg (required for Manim)

## 🚀 Getting Started

### Backend Setup

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
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory with:
   ```
   GROQ_API_KEY=your_groq_api_key
   FLASK_DEBUG=false
   PORT=5000
   ```

5. Run the backend server:
   ```bash
   python app.py
   ```

### Frontend Setup

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

## 🎯 Usage

1. Enter a text description of the animation you want to create
2. Click "Generate Animation"
3. Wait for the animation to be generated (may take a few moments)
4. Watch your animation!

### Example Prompts

- "A blue ball bouncing with a scaling shadow"
- "A rotating cube with changing colors"

## ⚠️ Important Notes

- The backend may take a minute to wake up after inactivity
- If you encounter an error, try refreshing the browser
- The current version uses a smaller LLM, so animations might not be exact matches to the prompts

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

- **Sourish** - [Portfolio](https://sourish.xyz)|[𝕏](https://x.com/sourize_)

## 🙏 Acknowledgments

- [Manim](https://github.com/ManimCommunity/manim) for the animation engine
- [Groq](https://groq.com) for the LLM API
- [Next.js](https://nextjs.org) for the frontend framework
- [Tailwind CSS](https://tailwindcss.com) for the styling

## 📞 Support

If you encounter any issues or have questions, please open an issue in the GitHub repository.

---

Made with ❤️ by Sourish