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
        title: "Empty prompt",
        description: "Please enter a prompt to generate an animation.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setError('');
    setVideoUrl('');
    if (videoRef.current) videoRef.current.load();

    try {
      toast({
        title: "Generating animation",
        description: "This may take a minute...",
      });

      const response = await axios.post(`${LLM_SERVICE_URL}/generate-code`, {
        prompt,
        quality: "m",
        timeout: 300,
      });

      const returnedUrl = response.data.videoUrl;
      setVideoUrl(returnedUrl + `?t=${Date.now()}`);

      toast({
        title: "Success!",
        description: "Your animation has been generated successfully.",
      });
    } catch (err: any) {
      const message = err.response?.data?.error || "Failed to generate animation. Please try again.";
      setError(message);
      toast({
        title: "Generation failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full flex flex-col items-center space-y-6 mt-4">
      <form onSubmit={handleSubmit} className="w-full max-w-2xl flex flex-col space-y-4 px-4">
        <Input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your animation..."
          className="text-lg py-6"
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Generating..." : "Generate Animation"}
        </Button>
      </form>

      {error && <p className="text-red-500 text-center">{error}</p>}

      {videoUrl && (
        <video
          ref={videoRef}
          key={videoUrl}
          controls
          className="max-w-full mt-6 border rounded-xl shadow-lg"
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      )}
    </div>
  );
}
