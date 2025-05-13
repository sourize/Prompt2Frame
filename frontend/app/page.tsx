'use client';

import { motion } from 'framer-motion';
import { useState, useRef } from 'react';
import axios from 'axios';

const examples = [
  "A bouncing ball with a shadow",
  "A rotating cube with changing colors",
  "A character walking from left to right"
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
    try {
      const response = await axios.post('http://localhost:5000/generate', { prompt });
      // Ensure the URL is properly constructed
      const videoPath = response.data.videoUrl;
      const fullUrl = `http://localhost:5000${videoPath}`;
      console.log('Video URL:', fullUrl); // Debug log
      setVideoUrl(fullUrl);
    } catch (err: any) {
      console.error('Error:', err); // Debug log
      setError(err.response?.data?.error || 'Failed to generate animation. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video error:', e); // Debug log
    setError('Failed to load video. Please try again.');
  };

  const videoUrlWithCacheBust = videoUrl ? `${videoUrl}?t=${Date.now()}` : '';

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
            <span role="img" aria-label="logo">🎬</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-center mb-1 tracking-tight">Text-to-Animation (Miaim)</h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-center text-gray-400 text-base font-medium"
          >
            Crafting Intelligent Animations from Text
          </motion.p>
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
              src={videoUrlWithCacheBust}
              controls
              playsInline
              className="w-full rounded-xl"
              onError={handleVideoError}
              key={videoUrlWithCacheBust} // Force re-render when URL changes
            >
              <source src={videoUrlWithCacheBust} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        ) : (
          <div className="text-gray-500 text-center w-full">
            {loading ? 'Generating animation...' : 'Your generated animation will appear here.'}
          </div>
        )}
      </motion.div>

      {/* Footer */}
      <footer className="text-center text-gray-500 text-sm mb-4">
        Made with <span className="text-pink-400">❤️</span> by Sourish
      </footer>
    </div>
  );
} 