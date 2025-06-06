"use client";

import { useRef, useState } from "react";
import axios from "axios";
import { toast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const LLM_SERVICE_URL = process.env.NEXT_PUBLIC_LLM_SERVICE_URL || "https://manim-llm-service.onrender.com";

export default function SearchInterface({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) {
  const [prompt, setPrompt] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!prompt.trim()) {
      toast({
        title: "Prompt Required",
        description: "Please enter a prompt before generating.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setError('');
    setVideoUrl('');

    try {
      toast({
        title: "Generating...",
        description: "Hang tight while we generate your animation!",
      });

      const response = await axios.post(`${LLM_SERVICE_URL}/generate-code`, {
        prompt,
        quality: "m", // 🔧 hardcoded medium
        timeout: 300,
      });

      const videoUrlFromBackend = response.data.videoUrl;
      setVideoUrl(`${videoUrlFromBackend}?t=${Date.now()}`);

      toast({
        title: "Success!",
        description: "Your animation is ready 🎬",
      });
    } catch (err: any) {
      const message = err.response?.data?.error || "Something went wrong. Try again.";
      setError(message);
      toast({
        title: "Failed to generate",
        description: message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full flex flex-col items-center space-y-6">
      <form onSubmit={handleSubmit} className="w-full max-w-xl flex flex-col items-center space-y-4">
        <Input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your animation..."
          className="w-full"
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Generating..." : "Generate"}
        </Button>
      </form>

      {error && <p className="text-red-500">{error}</p>}

      {videoUrl && (
        <video
          ref={videoRef}
          key={videoUrl}
          controls
          className="w-full max-w-3xl mt-6 rounded-xl shadow-md"
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      )}
    </div>
  );
}
