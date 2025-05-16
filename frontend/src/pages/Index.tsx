
import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowRight, Download, Play, Info, Video, Sparkles, MousePointerClick, MessageCircle, AlertCircle } from "lucide-react";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const examples = [
  "Draw a red circle and transform it into a square",
  "Draw a blue circle and transform it into a triangle",
  "Create a bouncing ball that changes colors",
  "Animate a growing neural network visualization"
];

const features = [
  { 
    title: "Mathematical Animations", 
    description: "Transform geometric concepts into visual animations with precision",
    icon: <Sparkles className="h-4 w-4" />
  },
  { 
    title: "Simple Prompting", 
    description: "Just describe what you want to see - no coding required",
    icon: <MessageCircle className="h-4 w-4" />
  },
  { 
    title: "Instant Generation", 
    description: "Get your custom animation in seconds",
    icon: <MousePointerClick className="h-4 w-4" />
  }
];

const Index = () => {
  const [prompt, setPrompt] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(false);
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
      videoRef.current.load(); // Force video reload
    }
    
    try {
      toast({
        title: "Generating animation",
        description: "This may take a minute...",
      });
      
      const response = await axios.post('https://anime2d.onrender.com/generate', { prompt });
      const videoPath = response.data.videoUrl;
      const fullUrl = `https://anime2d.onrender.com${videoPath}?t=${Date.now()}`; // Add timestamp to URL
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

  // Background animation variants for the blobs
  const blobVariants = {
    initial: { scale: 0.8, opacity: 0.7 },
    animate: { 
      scale: [0.8, 1.1, 0.8], 
      opacity: [0.7, 0.9, 0.7],
      transition: { 
        repeat: Infinity, 
        duration: 12,
        ease: "easeInOut" 
      }
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center px-4 py-10 md:py-12 overflow-hidden">
      {/* Patterned background */}
      <div 
        className="absolute inset-0 bg-grid-small-black/[0.2] -z-10" 
        style={{ backgroundSize: '32px 32px' }}
      />
      <div className="absolute inset-0 bg-background/80 backdrop-blur-[2px] -z-10" />
      
      {/* Animated background blobs - visible only on larger screens */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none hidden md:block">
        <motion.div 
          className="absolute top-[10%] left-[5%] w-[40vw] h-[40vw] rounded-full bg-primary/5 blur-3xl"
          variants={blobVariants}
          initial="initial"
          animate="animate"
          custom={0}
        />
        <motion.div 
          className="absolute bottom-[20%] right-[10%] w-[35vw] h-[35vw] rounded-full bg-primary/10 blur-3xl"
          variants={blobVariants}
          initial="initial"
          animate="animate"
          transition={{ delay: 2 }}
          custom={1}
        />
      </div>

      {/* Header with improved typography */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="relative w-full max-w-3xl text-center mb-6 md:mb-10"
      >
        <div className="inline-flex items-center justify-center mb-4">
          <motion.div 
            className="w-16 h-16 rounded-full bg-gradient-to-tr from-primary to-primary/70 flex items-center justify-center text-2xl shadow-lg"
            whileHover={{ scale: 1.05, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            <Video className="text-primary-foreground w-8 h-8" />
          </motion.div>
        </div>
        
        <motion.h1 
          className="text-4xl md:text-6xl font-bold tracking-tight mb-3 bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/80"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          Prompt2Frame
        </motion.h1>
        
        <motion.p
          className="text-lg md:text-xl text-muted-foreground max-w-xl mx-auto mb-3 leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          Transform your ideas into mathematical animations with AI
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="max-w-2xl mx-auto hidden md:block"
        >
          <Card className="bg-card/50 backdrop-blur-sm border-primary/10">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground leading-relaxed">
                Prompt2Frame uses AI to create mathematical animations from text descriptions. 
                Perfect for educators and content creators.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                {features.map((feature, idx) => (
                  <div key={idx} className="flex flex-col items-center text-center p-3 rounded-lg bg-background/50 border border-border/50">
                    <div className="bg-primary/10 p-2 rounded-full mb-2">
                      {feature.icon}
                    </div>
                    <h3 className="text-sm font-medium mb-1">{feature.title}</h3>
                    <p className="text-xs text-muted-foreground">{feature.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Tabs for content organization */}
      <div className="w-full max-w-3xl mb-6">
        <Tabs defaultValue="create" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="create">Create</TabsTrigger>
            <TabsTrigger value="info">Info</TabsTrigger>
          </TabsList>
          
          <TabsContent value="create" className="space-y-6">
            {/* Prompt Card with improved design */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
            >
              <Card className="shadow-md border-primary/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span>Create Animation</span>
                    <Badge variant="outline" className="ml-2 font-normal">
                      AI-Powered
                    </Badge>
                  </CardTitle>
                  {/* Removed redundant description text */}
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <Textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Describe your animation idea... (e.g. Draw a red circle and transform it into a square)"
                      className="min-h-[120px] resize-none focus:ring-primary"
                    />
                    
                    {/* Warning about backend limitations */}
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-2">
                      <AlertCircle size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-muted-foreground">
                        <strong className="font-medium text-amber-500">Important:</strong> The backend has limited capacity. Keep prompts concise and avoid complex requests. The system works best with simple geometric animations and basic transformations.
                      </p>
                    </div>
                    {/* Warning about backend limitations */}
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-2">
                      <AlertCircle size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-muted-foreground">
                        <strong className="font-medium text-amber-500">Important:</strong> If you get an error, refresh the page and try again.
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground mb-2 text-center">Example prompts:</p>
                      <div className="flex flex-wrap justify-center gap-2">
                        {examples.map((example, idx) => (
                          <motion.div key={idx} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                            <Badge 
                              variant="secondary" 
                              className="cursor-pointer" 
                              onClick={() => setPrompt(example)}
                            >
                              {example}
                            </Badge>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                    
                    <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                      <Button 
                        type="submit" 
                        className="w-full gap-2" 
                        disabled={loading}
                      >
                        {loading ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Generating
                          </>
                        ) : (
                          <>Generate Animation <ArrowRight size={16} /></>
                        )}
                      </Button>
                    </motion.div>
                  </form>
                </CardContent>
              </Card>
            </motion.div>

            {/* Video Output Card with improved design */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
            >
              <Card className="shadow-md border-primary/20">
                <CardHeader>
                  <CardTitle>Animation Output</CardTitle>
                  <CardDescription>
                    {videoUrl 
                      ? "Your generated animation is ready to view"
                      : "Your generated animation will appear here"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {error && (
                    <div className="p-4 mb-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive">
                      <div className="flex items-start gap-2">
                        <Info size={18} className="mt-0.5 flex-shrink-0" />
                        <p>{error}</p>
                      </div>
                    </div>
                  )}
                  
                  <div className="rounded-lg overflow-hidden bg-black/10 border border-border min-h-[240px] flex items-center justify-center">
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
                      <div className="text-muted-foreground p-8 text-center">
                        {loading ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                            className="mx-auto mb-3 w-8 h-8 border-2 border-primary border-t-transparent rounded-full"
                          />
                        ) : (
                          <Video size={40} className="mx-auto mb-3 text-muted-foreground/60" />
                        )}
                        <p>{loading ? 'Generating animation...' : 'Your animation will appear here'}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
                {videoUrl && (
                  <CardFooter className="flex justify-between">
                    <Button variant="outline" onClick={() => {
                      if (videoRef.current) {
                        videoRef.current.currentTime = 0;
                        videoRef.current.play();
                      }
                    }}>
                      <Play size={16} className="mr-2" /> Replay
                    </Button>
                    <Button onClick={handleDownload}>
                      <Download size={16} className="mr-2" /> Download
                    </Button>
                  </CardFooter>
                )}
              </Card>
            </motion.div>
          </TabsContent>
          
          <TabsContent value="info">
            <Card className="shadow-md border-primary/20">
              <CardHeader>
                <CardTitle>How It Works</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                  <div className="bg-card/50 p-4 rounded-lg border border-border space-y-2">
                    <h3 className="font-medium flex items-center gap-2">
                      <Badge className="h-6 w-6 rounded-full flex items-center justify-center p-0">1</Badge>
                      Enter Your Prompt
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Describe the animation you want to generate.
                    </p>
                  </div>
                  
                  <div className="bg-card/50 p-4 rounded-lg border border-border space-y-2">
                    <h3 className="font-medium flex items-center gap-2">
                      <Badge className="h-6 w-6 rounded-full flex items-center justify-center p-0">2</Badge>
                      AI Processing
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Our AI system interprets your description and generates the animation.
                    </p>
                  </div>
                  
                  <div className="bg-card/50 p-4 rounded-lg border border-border space-y-2">
                    <h3 className="font-medium flex items-center gap-2">
                      <Badge className="h-6 w-6 rounded-full flex items-center justify-center p-0">3</Badge>
                      View & Download
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Watch and download for presentations or social media.
                    </p>
                  </div>
                </div>
                
                <div className="pt-2 text-sm text-muted-foreground space-y-2">
                  <p className="flex items-center gap-2">
                    <Info size={16} className="text-primary" />
                    Wait a minute after inactivity (backend sleeps)
                  </p>
                  <p className="flex items-center gap-2">
                    <Info size={16} className="text-primary" />
                    If errors occur, refresh and try again
                  </p>
                  <p className="flex items-center gap-2">
                    <AlertCircle size={16} className="text-amber-500" />
                    Limited capacity - keep requests simple
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Footer with improved design */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 0.6 }}
        className="mt-auto pt-4 pb-6 w-full max-w-3xl"
      >
        <div className="relative p-4 rounded-lg bg-card/50 backdrop-blur-sm border border-primary/10">
          <div className="absolute inset-0 bg-dot-white/[0.2] rounded-lg -z-10" />
          <div className="text-center text-sm text-muted-foreground">
            <p className="mb-2 font-medium text-foreground/90">
              <span className="text-red-400 mr-1">❤️</span>
              Built by
              <HoverCard>
                <HoverCardTrigger asChild>
                  <a 
                    href="https://x.com/sourize_" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:underline transition-colors mx-1"
                  >
                    Sourish
                  </a>
                </HoverCardTrigger>
                <HoverCardContent className="w-64">
                  <div className="space-y-1">
                    <h4 className="text-sm font-semibold">About the Creator</h4>
                    <p className="text-xs text-muted-foreground">
                      Passionate about AI, animations, and making complex concepts accessible.
                    </p>
                  </div>
                </HoverCardContent>
              </HoverCard>
            </p>
            <div className="flex justify-center gap-4 mt-2">
              <a 
                href="https://github.com/sourize" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline"
              >
                GitHub
              </a>
              <a 
                href="https://sourish.xyz" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline"
              >
                Portfolio
              </a>
            </div>
          </div>
        </div>
      </motion.footer>
    </div>
  );
};

export default Index;
