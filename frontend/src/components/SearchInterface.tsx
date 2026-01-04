import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import {
  ArrowRight,
  Download,
  Play,
  Video,
  AlertCircle,
  Sparkles,
  Zap,
  Circle
} from "lucide-react";

// Point this at your local proxy which forwards to the backend
const BACKEND_URL = '/api'; // Relative path for Vercel/proxied requests

const SearchInterface = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  const [prompt, setPrompt] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');
  const [loadingStep, setLoadingStep] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Loading steps with their descriptions
  const loadingSteps = [
    "🔍 Analyzing your prompt...",
    "🤖 Generating animation code...",
    "🎬 Rendering your animation...",
    "✨ Finalizing the video..."
  ];

  // Tips to show during loading
  const loadingTips = [
    "💡 Tip: Simple geometric shapes render faster",
    "✨ Tip: Try adding color transitions for dynamic results",
    "🎨 Tip: Describe motion and transformations clearly",
    "⚡ Tip: Shorter prompts usually work best"
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      toast({
        title: "Empty prompt",
        description: "Please enter a prompt to generate an animation.",
        variant: "destructive",
      });
      return;
    }
    setLoading(true);
    setError('');
    setVideoUrl('');
    setLoadingStep(0);
    if (videoRef.current) {
      videoRef.current.load();
    }

    // Start the loading steps animation
    const stepInterval = setInterval(() => {
      setLoadingStep(prev => (prev + 1) % loadingSteps.length);
    }, 4000); // Change step every 4 seconds

    try {
      toast({
        title: "✨ Generating animation",
        description: "This may take a moment...",
      });

      const response = await axios.post(
        `${BACKEND_URL}/generate`,
        {
          prompt,
          quality: 'm',
          timeout: 300
        }
      );

      clearInterval(stepInterval);

      const returnedUrl: string = response.data.videoUrl;
      const fullUrl = `${BACKEND_URL}${returnedUrl}?t=${Date.now()}`;
      console.log('Video URL:', fullUrl);
      setVideoUrl(fullUrl);

      toast({
        title: "🎉 Success!",
        description: "Your animation is ready!",
      });
    } catch (err: any) {
      clearInterval(stepInterval);
      console.error('Error:', err);
      setError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to generate animation. Please try again.');
      toast({
        title: "Generation failed",
        description: err.response?.data?.detail?.message || 'Failed to generate animation',
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video error:', e);
    setError('Failed to load video. Please try again.');
  };

  const handleDownload = () => {
    if (videoUrl) {
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = `prompt2frame-${Date.now()}.mp4`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast({
        title: "📥 Download started",
        description: "Your animation is being downloaded.",
      });
    }
  };

  const examplePrompts = [
    "Draw a red circle and transform it into a square",
    "Create a bouncing ball that changes colors",
    "Animate a growing neural network visualization",
    "Make a simple pendulum swinging motion"
  ];

  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen px-4 sm:px-6 py-8 sm:py-12">
      <div className="w-full max-w-3xl mx-auto space-y-6 sm:space-y-8 relative z-10">

        {/* Header Section with Premium Styling */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="text-center space-y-3 sm:space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 mb-3 sm:mb-4">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-xs text-gray-300 font-medium">AI-Powered Animation</span>
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-2 sm:mb-3 px-4">
            <span className="gradient-text">Prompt2Frame</span>
          </h1>

          <p className="text-gray-100 text-sm sm:text-base max-w-xl mx-auto leading-relaxed px-4">
            Turn your ideas into stunning 2D animations with AI
          </p>
        </motion.div>

        {/* Premium Search Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="w-full"
        >
          <form onSubmit={handleSubmit} className="w-full">
            <div className="relative glass-card rounded-xl p-0.5 smooth-hover">
              <div className="relative bg-gray-900/50 rounded-xl">
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the animation you want to create..."
                  className="w-full bg-transparent border-0 text-white placeholder-gray-400 resize-none px-4 sm:px-5 py-3 sm:py-4 pr-12 sm:pr-14 text-sm leading-relaxed focus:ring-0 focus:outline-none min-h-[60px] rounded-xl"
                  rows={1}
                  style={{
                    minHeight: '60px',
                    maxHeight: '180px',
                    height: 'auto',
                  }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = '60px';
                    const newHeight = Math.min(target.scrollHeight, 180);
                    target.style.height = `${newHeight}px`;
                  }}
                />

                {/* Submit button - larger touch target on mobile */}
                <div className="absolute right-2 sm:right-3 bottom-2 sm:bottom-3">
                  <Button
                    type="submit"
                    disabled={loading || !prompt.trim()}
                    className="h-10 w-10 sm:h-9 sm:w-9 p-0 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed shadow-md transition-all duration-200 active:scale-95"
                  >
                    {loading ? (
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                      >
                        <Circle className="h-5 w-5" />
                      </motion.div>
                    ) : (
                      <ArrowRight className="h-5 w-5" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </form>
        </motion.div>

        {/* Enhanced Example Prompts - responsive grid */}
        {!videoUrl && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-2 sm:space-y-3"
          >
            <p className="text-xs uppercase tracking-wide text-gray-400 font-medium mb-2">Try these examples</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {examplePrompts.map((example, index) => (
                <motion.button
                  key={index}
                  onClick={() => setPrompt(example)}
                  className="group glass-card rounded-lg p-3 text-left smooth-hover active:scale-98 touch-manipulation"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-start gap-2.5">
                    <Zap className="w-3.5 h-3.5 text-indigo-300 mt-0.5 flex-shrink-0" />
                    <span className="text-xs text-gray-100 leading-relaxed">{example}</span>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Enhanced Video Output Section */}
        <AnimatePresence>
          {(videoUrl || error || loading) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.6 }}
              className="w-full"
            >
              <Card className="glass-card border-0 overflow-hidden">
                <CardContent className="p-4 sm:p-5 space-y-3 sm:space-y-4">
                  {/* Header - responsive */}
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className="w-8 h-8 sm:w-9 sm:h-9 bg-gradient-to-tr from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Video className="w-4 h-4 text-white" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-white font-semibold text-sm sm:text-base truncate">Animation Output</h3>
                      <p className="text-gray-300 text-xs truncate">
                        {videoUrl ? "✨ Ready to view" : loading ? "⏳ Generating..." : "❌ Generation failed"}
                      </p>
                    </div>
                  </div>

                  {/* Error Display */}
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="p-4 rounded-xl bg-red-500/10 border border-red-500/20"
                    >
                      <div className="flex items-start gap-3">
                        <AlertCircle size={20} className="text-red-400 mt-0.5 flex-shrink-0" />
                        <div className="space-y-2">
                          <p className="text-red-300 font-medium text-base">Generation Failed</p>
                          <p className="text-sm text-gray-100">{error}</p>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* Video Player or Loading - responsive */}
                  <div className="rounded-lg overflow-hidden bg-black/40 border border-white/5 min-h-[240px] sm:min-h-[280px] flex items-center justify-center">
                    {videoUrl ? (
                      <div className="flex items-center justify-center w-full h-full">
                        <video
                          ref={videoRef}
                          src={videoUrl}
                          controls
                          playsInline
                          className="w-auto h-full max-w-full max-h-full rounded-lg mx-auto"
                          onError={handleVideoError}
                          key={videoUrl}
                          autoPlay={false}
                          preload="auto"
                        >
                          <source src={videoUrl} type="video/mp4" />
                          Your browser does not support the video tag.
                        </video>
                      </div>
                    ) : loading ? (
                      <div className="text-center space-y-4 sm:space-y-5 p-6 sm:p-8">
                        {/* Animated Loading Spinner - responsive */}
                        <motion.div
                          className="relative mx-auto w-12 h-12 sm:w-16 sm:h-16"
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                        >
                          <div className="absolute inset-0 border-4 border-indigo-500/30 rounded-full"></div>
                          <div className="absolute inset-0 border-4 border-transparent border-t-indigo-500 rounded-full"></div>
                        </motion.div>

                        {/* Loading Text */}
                        <div className="space-y-2">
                          <motion.p
                            key={loadingStep}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="text-base font-medium text-white"
                          >
                            {loadingSteps[loadingStep]}
                          </motion.p>

                          <motion.p
                            key={`tip-${loadingStep}`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-xs text-gray-400"
                          >
                            {loadingTips[loadingStep]}
                          </motion.p>

                          {/* Progress Dots */}
                          <div className="flex justify-center gap-1.5 pt-2">
                            {loadingSteps.map((_, index) => (
                              <motion.div
                                key={index}
                                className={`w-1.5 h-1.5 rounded-full ${index === loadingStep ? 'bg-indigo-500' : 'bg-gray-700'
                                  }`}
                                animate={{
                                  scale: index === loadingStep ? 1.3 : 1,
                                  opacity: index === loadingStep ? 1 : 0.5
                                }}
                                transition={{ duration: 0.3 }}
                              />
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-gray-500 text-center p-8">
                        <Video size={48} className="mx-auto mb-3 opacity-50" />
                        <p>Your animation will appear here</p>
                      </div>
                    )}
                  </div>

                  {/* Action Buttons - responsive stack on mobile */}
                  {videoUrl && (
                    <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-2">
                      <Button
                        variant="ghost"
                        className="flex-1 bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 min-h-[44px] touch-manipulation shadow-none"
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = 0;
                            videoRef.current.play();
                          }
                        }}
                      >
                        <Play size={16} className="mr-2" /> Replay
                      </Button>
                      <Button
                        className="flex-1 bg-[#2d3250] hover:bg-[#3d4260] text-white min-h-[44px] touch-manipulation shadow-none border border-white/5"
                        onClick={handleDownload}
                      >
                        <Download size={16} className="mr-2" /> Download
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default SearchInterface;
