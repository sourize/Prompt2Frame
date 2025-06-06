import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import { ArrowRight, Download, Play, Video, AlertCircle, Paperclip, Mic, Camera, Search, Globe } from "lucide-react";
import SuggestedQuestions from "./SuggestedQuestions";

const SearchInterface = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  const [prompt, setPrompt] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);

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
    if (videoRef.current) {
      videoRef.current.load();
    }
    try {
      toast({
        title: "Generating animation",
        description: "This may take a minute...",
      });
      const response = await axios.post('https://anime2d.onrender.com/generate', { prompt });
      const videoPath = response.data.videoUrl;
      const fullUrl = `https://anime2d.onrender.com${videoPath}?t=${Date.now()}`;
      console.log('Video URL:', fullUrl);
      setVideoUrl(fullUrl);
      toast({
        title: "Success!",
        description: "Your animation has been generated successfully.",
      });
    } catch (err: any) {
      console.error('Error:', err);
      setError(err.response?.data?.error || 'Failed to generate animation. Please try again.');
      toast({
        title: "Generation failed",
        description: err.response?.data?.error || 'Failed to generate animation. Please try again.',
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
        title: "Download started",
        description: "Your animation is being downloaded.",
      });
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setPrompt(suggestion);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-6">
      <div className="w-full max-w-2xl mx-auto space-y-8">
        
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <h1 className="text-4xl font-bold text-white mb-2">Prompt2Frame</h1>
          <p className="text-gray-400 text-lg mb-8">Turn prompts into animations</p>
        </motion.div>

        {/* Centered Search Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="w-full"
        >
          <form onSubmit={handleSubmit} className="w-full">
            <div className="relative bg-gray-800/90 rounded-xl border border-gray-700/50 backdrop-blur-sm hover:border-gray-600/50 transition-all duration-200">
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask a question..."
                className="w-full bg-transparent border-0 text-white placeholder-gray-400 resize-none px-6 py-4 pr-16 text-base leading-relaxed focus:ring-0 focus:outline-none min-h-[60px] rounded-xl overflow-hidden"
                rows={1}
                style={{
                  minHeight: '60px',
                  maxHeight: '200px',
                  height: 'auto',
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = '60px';
                  target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
                }}
              />

              {/* Submit button */}
              <div className="absolute right-3 bottom-3">
                <Button
                  type="submit"
                  disabled={loading || !prompt.trim()}
                  className="h-8 w-8 p-0 bg-gray-600/80 text-white hover:bg-gray-500/80 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <ArrowRight className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </form>
        </motion.div>

        {/* Suggested Questions with animation examples */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="w-full space-y-3"
        >
          <div 
            className="flex items-center gap-2 text-gray-400 hover:text-gray-300 transition-colors cursor-pointer"
            onClick={() => handleSuggestionClick("Draw a red circle and transform it into a square")}
          >
            <ArrowRight className="w-4 h-4" />
            <Video className="w-4 h-4" />
            <span className="text-sm">Draw a red circle and transform it into a square</span>
          </div>
          <div 
            className="flex items-center gap-2 text-gray-400 hover:text-gray-300 transition-colors cursor-pointer"
            onClick={() => handleSuggestionClick("Create a bouncing ball that changes colors")}
          >
            <ArrowRight className="w-4 h-4" />
            <Video className="w-4 h-4" />
            <span className="text-sm">Create a bouncing ball that changes colors</span>
          </div>
          <div 
            className="flex items-center gap-2 text-gray-400 hover:text-gray-300 transition-colors cursor-pointer"
            onClick={() => handleSuggestionClick("Animate a growing neural network visualization")}
          >
            <ArrowRight className="w-4 h-4" />
            <Video className="w-4 h-4" />
            <span className="text-sm">Animate a growing neural network visualization</span>
          </div>
          <div 
            className="flex items-center gap-2 text-gray-400 hover:text-gray-300 transition-colors cursor-pointer"
            onClick={() => handleSuggestionClick("Make a simple pendulum swinging motion")}
          >
            <ArrowRight className="w-4 h-4" />
            <Video className="w-4 h-4" />
            <span className="text-sm">Make a simple pendulum swinging motion</span>
          </div>
        </motion.div>

        {/* Video Output Section - Only show when there's content */}
        {(videoUrl || error || loading) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="w-full"
          >
            <Card className="bg-gray-800/50 border-gray-700/50 backdrop-blur-sm">
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <Video className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-medium">Animation Output</h3>
                    <p className="text-gray-400 text-sm">
                      {videoUrl 
                        ? "Your generated animation is ready to view"
                        : loading 
                        ? "Generating your animation..."
                        : "Generation failed"}
                    </p>
                  </div>
                </div>

                {error && (
                  <div className="p-4 mb-4 rounded-lg bg-red-500/10 border border-red-500/30">
                    <div className="flex items-start gap-3">
                      <AlertCircle size={20} className="text-red-400 mt-0.5 flex-shrink-0" />
                      <div className="space-y-2">
                        <p className="text-red-400 font-medium">Generation Failed</p>
                        <p className="text-sm text-gray-300">{error}</p>
                        <div className="space-y-2">
                          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                            <p className="text-xs text-gray-300">
                              <strong className="font-medium text-amber-400">Tip:</strong> The backend has limited capacity. Keep prompts concise and avoid complex requests. The system works best with simple geometric animations and basic transformations.
                            </p>
                          </div>
                        </div>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="mt-2 bg-gray-700/50 border-gray-600 text-gray-300 hover:bg-gray-600/50"
                          onClick={() => window.location.reload()}
                        >
                          Refresh Page
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                <div className="rounded-lg overflow-hidden bg-black/20 border border-gray-700/50 min-h-[240px] flex items-center justify-center">
                  {videoUrl ? (
                    <video
                      ref={videoRef}
                      src={videoUrl}
                      controls
                      playsInline
                      className="w-full rounded-lg"
                      onError={handleVideoError}
                      key={videoUrl}
                      autoPlay={false}
                      preload="auto"
                    >
                      <source src={videoUrl} type="video/mp4" />
                      Your browser does not support the video tag.
                    </video>
                  ) : (
                    <div className="text-gray-400 p-8 text-center">
                      {loading ? (
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                          className="mx-auto mb-3 w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"
                        />
                      ) : (
                        <Video size={40} className="mx-auto mb-3 text-gray-500" />
                      )}
                      <p>{loading ? 'Generating animation...' : 'Your animation will appear here'}</p>
                    </div>
                  )}
                </div>

                {videoUrl && (
                  <div className="flex justify-between mt-4 pt-4 border-t border-gray-700/50">
                    <Button 
                      variant="outline" 
                      className="bg-gray-700/50 border-gray-600 text-gray-300 hover:bg-gray-600/50"
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
                      className="bg-white text-black hover:bg-gray-200"
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
      </div>
    </div>
  );
};

export default SearchInterface;
