"use client";

import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Play, Pause, RotateCcw, Download } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

const CustomSlider = ({
    value,
    onChange,
    className,
}: {
    value: number;
    onChange: (value: number) => void;
    className?: string;
}) => {
    return (
        <div
            className={cn(
                "relative w-full h-6 flex items-center cursor-pointer group touch-none", // Increased height for touch target
                className
            )}
            onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const percentage = (x / rect.width) * 100;
                onChange(Math.min(Math.max(percentage, 0), 100));
            }}
        >
            {/* Visual Track */}
            <div className="w-full h-1 bg-white/20 rounded-full relative overflow-hidden group-hover:h-1.5 transition-all duration-300">
                <motion.div
                    className="absolute top-0 left-0 h-full bg-white rounded-full"
                    style={{ width: `${value}%` }}
                    initial={{ width: 0 }}
                    animate={{ width: `${value}%` }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
            </div>
        </div>
    );
};

const VideoPlayer = ({ src, onError, onDownload }: { src: string; onError?: (e: any) => void; onDownload?: () => void }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [playbackSpeed, setPlaybackSpeed] = useState(1);
    const [showControls, setShowControls] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);

    const togglePlay = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
            } else {
                videoRef.current.play();
            }
            setIsPlaying(!isPlaying);
            setShowControls(true); // Ensure controls show on interaction
        }
    };

    const handleReplay = () => {
        if (videoRef.current) {
            videoRef.current.currentTime = 0;
            videoRef.current.play();
            setIsPlaying(true);
            setShowControls(true);
        }
    };

    const handleDownload = () => {
        if (onDownload) {
            onDownload();
        } else if (src) {
            const link = document.createElement('a');
            link.href = src;
            link.download = `prompt2frame-${Date.now()}.mp4`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            const progress =
                (videoRef.current.currentTime / videoRef.current.duration) * 100;
            setProgress(isFinite(progress) ? progress : 0);
            setCurrentTime(videoRef.current.currentTime);
            setDuration(videoRef.current.duration);
        }
    };

    const handleSeek = (value: number) => {
        if (videoRef.current && videoRef.current.duration) {
            const time = (value / 100) * videoRef.current.duration;
            if (isFinite(time)) {
                videoRef.current.currentTime = time;
                setProgress(value);
            }
        }
    };

    const setSpeed = (speed: number) => {
        if (videoRef.current) {
            videoRef.current.playbackRate = speed;
            setPlaybackSpeed(speed);
        }
    };

    return (
        <motion.div
            className="relative w-full max-w-4xl mx-auto rounded-3xl overflow-hidden bg-[#11111198] shadow-[0_0_20px_rgba(0,0,0,0.2)] backdrop-blur-sm group border border-white/40"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            onMouseEnter={() => setShowControls(true)}
            onMouseLeave={() => setShowControls(false)}
            onClick={() => setShowControls(prev => !prev)} // Toggle controls on tap anywhere on component
        >
            <video
                ref={videoRef}
                className="w-full aspect-video object-contain bg-black/50"
                onTimeUpdate={handleTimeUpdate}
                src={src}
                onClick={(e) => {
                    e.stopPropagation(); // Prevent double toggle
                    togglePlay();
                }}
                onError={onError}
                playsInline
            />

            <AnimatePresence>
                {(showControls || !isPlaying) && ( // Always show controls when paused
                    <motion.div
                        className="absolute bottom-0 mx-auto max-w-xl left-0 right-0 p-3 sm:p-4 m-2 bg-[#111111e6] backdrop-blur-md rounded-2xl border border-white/5"
                        initial={{ y: 20, opacity: 0, filter: "blur(10px)" }}
                        animate={{ y: 0, opacity: 1, filter: "blur(0px)" }}
                        exit={{ y: 20, opacity: 0, filter: "blur(10px)" }}
                        transition={{ duration: 0.4, ease: "circInOut" }}
                        onClick={(e) => e.stopPropagation()} // Prevent closing controls when clicking controls
                    >
                        {/* Progress Bar Row */}
                        <div className="flex items-center gap-3 mb-3">
                            <span className="text-white/80 text-xs font-medium tabular-nums min-w-[35px]">
                                {formatTime(currentTime)}
                            </span>
                            <CustomSlider
                                value={progress}
                                onChange={handleSeek}
                                className="flex-1"
                            />
                            <span className="text-white/80 text-xs font-medium tabular-nums min-w-[35px] text-right">
                                {formatTime(duration)}
                            </span>
                        </div>

                        {/* Controls Row */}
                        <div className="flex flex-wrap items-center justify-between gap-y-2 gap-x-2">
                            {/* Left side: Play and Replay */}
                            <div className="flex items-center gap-1">
                                <Button
                                    onClick={togglePlay}
                                    variant="ghost"
                                    size="icon"
                                    className="w-8 h-8 sm:w-10 sm:h-10 text-white hover:bg-white/10 hover:text-white rounded-full"
                                >
                                    {isPlaying ? (
                                        <Pause className="h-4 w-4 sm:h-5 sm:w-5 fill-current" />
                                    ) : (
                                        <Play className="h-4 w-4 sm:h-5 sm:w-5 fill-current" />
                                    )}
                                </Button>

                                <Button
                                    onClick={handleReplay}
                                    variant="ghost"
                                    size="icon"
                                    className="w-8 h-8 sm:w-10 sm:h-10 text-white hover:bg-white/10 hover:text-white rounded-full"
                                >
                                    <RotateCcw className="h-4 w-4 sm:h-5 sm:w-5" />
                                </Button>
                            </div>

                            {/* Right side: Download and Speed */}
                            <div className="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
                                <Button
                                    onClick={handleDownload}
                                    variant="ghost"
                                    size="icon"
                                    className="w-8 h-8 sm:w-10 sm:h-10 text-white hover:bg-white/10 hover:text-white rounded-full"
                                    title="Download Video"
                                >
                                    <Download className="h-4 w-4 sm:h-5 sm:w-5" />
                                </Button>

                                <div className="flex items-center bg-white/5 rounded-lg p-0.5 border border-white/5">
                                    {[0.5, 1, 1.5, 2].map((speed) => (
                                        <button
                                            key={speed}
                                            onClick={() => setSpeed(speed)}
                                            className={cn(
                                                "text-[10px] sm:text-xs font-medium px-2 py-1 sm:px-2.5 sm:py-1.5 rounded-md transition-all duration-200",
                                                playbackSpeed === speed
                                                    ? "bg-white text-black shadow-sm"
                                                    : "text-white/70 hover:text-white hover:bg-white/10"
                                            )}
                                        >
                                            {speed}x
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default VideoPlayer;
