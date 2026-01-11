import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import VideoGenerationPlan from "@/components/ui/video-generation-plan";
import { AlertCard } from "@/components/ui/alert-card";
import VideoPlayer from "@/components/ui/video-player";
import { HoverButton } from "@/components/ui/hover-button";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { PromptSuggestion } from "@/components/ui/prompt-suggestion";
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

// Backend URL configuration
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860';

const SearchInterface = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  const [prompt, setPrompt] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');
  const [loadingStep, setLoadingStep] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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
    }, 2000); // Faster updates (2s)

    try {

      const token = import.meta.env.VITE_HF_TOKEN;
      const response = await axios.post(
        `${BACKEND_URL}/generate`,
        {
          prompt,
          quality: 'm',
          timeout: 800
        },
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        }
      );

      clearInterval(stepInterval);

      const returnedUrl: string = response.data.videoUrl;

      // Complete remaining steps quickly before showing video
      const currentStepAtCompletion = loadingStep;
      if (currentStepAtCompletion < 3) {
        // Quickly show remaining steps
        for (let i = currentStepAtCompletion + 1; i <= 3; i++) {
          await new Promise(resolve => setTimeout(resolve, 300)); // 300ms per step
          setLoadingStep(i);
        }
        // Brief pause on final step
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // Use backend URL from env or default to localhost
      const backendHost = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860';
      const fullUrl = `${backendHost}${returnedUrl}`;
      console.log('Video URL:', fullUrl);

      // Handle Private HF Spaces by fetching with token
      const hfToken = import.meta.env.VITE_HF_TOKEN;
      if (hfToken) {
        try {
          const videoRes = await fetch(fullUrl, {
            headers: { Authorization: `Bearer ${hfToken}` }
          });
          if (!videoRes.ok) throw new Error(`Video fetch failed: ${videoRes.statusText}`);
          const blob = await videoRes.blob();
          const objectUrl = URL.createObjectURL(blob);
          setVideoUrl(objectUrl);
        } catch (e) {
          console.error("Failed to fetch private video:", e);
          // Fallback to direct URL if fetch fails
          setVideoUrl(fullUrl);
        }
      } else {
        setVideoUrl(fullUrl);
      }

    } catch (err: any) {
      clearInterval(stepInterval);
      console.error('Error:', err);
      setError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to generate animation. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video error:', e);
    setVideoUrl(''); // Clear video URL so AlertCard can show
    setError('Failed to load video. The backend service might need a moment to wake up.');
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
    <div className="relative flex flex-col items-center justify-center min-h-screen px-4 sm:px-6 pt-2 pb-8 sm:py-12">
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

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-serif font-medium mb-3 sm:mb-4 px-4 tracking-tight text-white">
            Prompt2Frame
          </h1>

          <p className="text-gray-300 text-sm sm:text-base max-w-xl mx-auto leading-relaxed px-4 mb-6">
            Turn your ideas into stunning 2D animations with AI
          </p>

          <div className="flex items-center justify-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[10px] font-medium text-green-400 uppercase tracking-wider">Available on Web</span>
            </div>
          </div>
        </motion.div>

        {/* Premium Search Input and Suggestions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="w-full space-y-4"
        >
          <div className="relative">
            <PromptInput
              value={prompt}
              onValueChange={setPrompt}
              onSubmit={() => handleSubmit({ preventDefault: () => { } } as React.FormEvent)}
              loading={loading}
              className="rounded-3xl border border-white/40 bg-black/40 backdrop-blur-md shadow-2xl focus-within:border-indigo-500/50 transition-all duration-300"
            >
              <PromptInputTextarea
                ref={inputRef}
                placeholder="Describe the animation you want to create..."
                className="text-white placeholder:text-gray-500 min-h-[40px] py-3 px-6 sm:text-base !bg-transparent !border-0 focus:ring-0 shadow-none ring-0 focus-visible:ring-0"
                style={{ backgroundColor: 'transparent', border: 'none', boxShadow: 'none' }}
              />
              <PromptInputActions className="justify-end pt-2 pb-3 pr-3">
                <Button
                  onClick={() => handleSubmit({ preventDefault: () => { } } as React.FormEvent)}
                  disabled={loading || !prompt.trim()}
                  className={cn(
                    "h-10 w-10 p-0 rounded-xl transition-all duration-200",
                    prompt.trim()
                      ? "bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/20"
                      : "bg-white/10 text-gray-500 hover:bg-white/20"
                  )}
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
              </PromptInputActions>
            </PromptInput>
          </div>

          {/* Suggestions - Only show when no video */}
          {!videoUrl && !loading && (
            <div className="flex flex-wrap gap-2 justify-center px-4">
              {examplePrompts.map((example) => (
                <PromptSuggestion
                  key={example}
                  onClick={() => setPrompt(example)}
                  variant="outline"
                  className="bg-white/5 border-white/10 hover:bg-white/10 text-gray-300 hover:text-white transition-colors rounded-full"
                >
                  {example}
                </PromptSuggestion>
              ))}
            </div>
          )}
        </motion.div>

        {/* Video Generation Plan - Shows during loading BELOW input */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
              className="w-full overflow-hidden"
            >
              <VideoGenerationPlan currentStep={loadingStep} isVideoReady={!!videoUrl} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Alert Card - Shows ONLY when there's an error */}
        <AnimatePresence>
          {error && !loading && !videoUrl && (
            <div className="w-full flex justify-center">
              <AlertCard
                isVisible={!!error}
                title="Generation Failed"
                description="Failed to generate video. The backend service might be asleep and will take 1-2 minutes to wake up. Please try again in a moment."
                buttonText="Try Again"
                onButtonClick={() => window.location.reload()}
                icon={<AlertCircle className="h-6 w-6 text-destructive-foreground" />}
              />
            </div>
          )}
        </AnimatePresence>

        {/* Video Player Only */}
        <AnimatePresence mode="wait">
          {videoUrl && !error && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="w-full space-y-6"
            >
              <VideoPlayer src={videoUrl} onError={(e: any) => handleVideoError(e)} onDownload={handleDownload} />

              <div className="flex justify-center">
                <HoverButton
                  onClick={() => {
                    setVideoUrl('');
                    // Optional: setPrompt(''); // Keep prompt for tweaking? 
                    // Let's keep it so user can modify. 
                    // Scroll to top or focus
                    setTimeout(() => {
                      inputRef.current?.focus();
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }, 100);
                  }}
                >
                  Generate New Animation
                </HoverButton>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div >
    </div >
  );
};

export default SearchInterface;
