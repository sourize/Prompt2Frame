'use client';

import { motion } from 'framer-motion';
import { useState, useRef } from 'react';
import axios from 'axios';

const examples = [
  "Draw a red circle and transform it into a square",
  "Draw a Blue Circle and transform it into a triangle",
];

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setVideoUrl('');
    if (videoRef.current) {
      videoRef.current.load(); // Force video reload
    }
    try {
      const response = await axios.post('https://anime2d.onrender.com/generate', { prompt });

      const videoPath = response.data.videoUrl;
      const fullUrl = `https://anime2d.onrender.com${videoPath}?t=${Date.now()}`; // Add timestamp to URL
      console.log('Video URL:', fullUrl);
      setVideoUrl(fullUrl);
    } catch (err: any) {
      console.error('Error:', err);
      setError(err.response?.data?.error || 'Failed to generate animation. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video error:', e);
    setError('Failed to load video. Please try again.');
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-b from-[#18181b] to-[#23272f] px-2">
      {/* Header Card */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="w-full max-w-xl bg-card rounded-2xl shadow-card p-8 flex flex-col items-center mb-8 mt-8"
      >
        <div className="flex flex-col items-center mb-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-primary to-secondary flex items-center justify-center text-3xl font-bold mb-2 select-none shadow-lg">
            <span role="img" aria-label="logo">🎞️</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-center mb-1 tracking-tight">Prompt2Frame</h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-center text-gray-400 text-base font-medium"
          >
            Crafting Intelligent Animations from Text
          </motion.p>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-center text-gray-500 text-sm mt-4 max-w-md"
          >
            Transform your ideas into mathematical animations. Create geometric shapes, 
            morphing transformations, neural networks, and mathematical concepts. 
            From simple circles to complex mathematical visualizations, bring your 
            mathematical ideas to life through elegant animations.
          </motion.p>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="text-center text-gray-500 text-sm mt-10 space-y-2"
          >
            <p>• Wait for a minute since the backend gets into sleep mode after inactivity</p>
            <p>• If you get an error, refresh the browser and retry</p>
          </motion.div>
        </div>
      </motion.div>

      {/* Prompt Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.7 }}
        className="w-full max-w-xl bg-card rounded-2xl shadow-card p-8 flex flex-col items-center mb-8"
      >
        <form onSubmit={handleSubmit} className="w-full flex flex-col items-center gap-4">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your animation idea..."
            className="w-full p-4 rounded-xl bg-surface border border-gray-700 focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none transition-all duration-200 min-h-[80px] text-white mb-2 shadow resize-none"
            rows={3}
          />
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="w-full bg-primary hover:bg-secondary text-white font-semibold py-3 px-6 rounded-xl transition-colors duration-200 shadow"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Generating...' : 'Generate Animation'}
          </motion.button>
        </form>
        {/* Example Prompts */}
        <div className="w-full mt-6">
          <h2 className="text-base font-semibold mb-3 text-gray-300">Example Prompts</h2>
          <div className="flex flex-row flex-wrap gap-2 justify-center">
            {examples.map((example, idx) => (
              <motion.button
                key={idx}
                whileHover={{ scale: 1.07 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setPrompt(example)}
                className="px-4 py-2 rounded-full bg-surface text-gray-200 hover:bg-primary hover:text-white transition-colors duration-200 border border-gray-700 text-sm shadow whitespace-nowrap"
                type="button"
              >
                {example}
              </motion.button>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Video Output Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.7 }}
        className="w-full max-w-xl bg-card rounded-2xl shadow-card p-8 flex flex-col items-center mb-8"
      >
        {error && (
          <div className="p-4 rounded-xl bg-red-500/20 border border-red-500 text-red-200 mb-4 w-full text-center">
            {error}
          </div>
        )}
        {videoUrl ? (
          <div className="rounded-xl overflow-hidden bg-surface w-full">
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              playsInline
              className="w-full rounded-xl"
              onError={handleVideoError}
              key={videoUrl} // Force re-render when URL changes
              autoPlay={false}
              preload="auto"
            >
              <source src={videoUrl} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            <div className="mt-6 text-center">
              <p className="text-gray-400 text-sm font-medium tracking-wide">
                Thanks for using{' '}
                <span className="text-primary font-semibold">Prompt2Frame</span>
              </p>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-center w-full">
            {loading ? 'Generating animation...' : 'Your generated animation will appear here.'}
          </div>
        )}
      </motion.div>

      {/* Footer */}
      <footer className="text-center text-gray-500 text-sm mb-4">
        Made with <span className="text-pink-400">❤️</span> by{' '}
        <a 
          href="https://x.com/sourize_" 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary hover:text-secondary transition-colors"
        >
          Sourish
        </a>
        {' • '}
        <a 
          href="https://github.com/sourize" 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary hover:text-secondary transition-colors"
        >
          GitHub
        </a>
        {' • '}
        <a 
          href="https://sourish.xyz" 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary hover:text-secondary transition-colors"
        >
          Portfolio
        </a>
      </footer>
    </div>
  );
} 