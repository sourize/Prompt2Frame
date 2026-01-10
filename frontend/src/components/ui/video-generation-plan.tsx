"use client";

import React, { useState, useEffect } from "react";

interface VideoGenerationPlanProps {
    currentStep: number; // 0 = expanding, 1 = generating, 2 = rendering, 3 = completed
    isVideoReady?: boolean;
}

export default function VideoGenerationPlan({
    currentStep = 0,
    isVideoReady = false
}: VideoGenerationPlanProps) {
    const [displayText, setDisplayText] = useState("");
    const [charIndex, setCharIndex] = useState(0);

    const steps = [
        "Analyzing your prompt...",
        "Expanding prompt requirements...",
        "Generating Manim code...",
        "Rendering animation...",
    ];

    const currentStepText = isVideoReady ? "Video ready!" : (steps[currentStep] || steps[0]);

    // Typewriter effect
    useEffect(() => {
        setCharIndex(0);
        setDisplayText("");
    }, [currentStep, isVideoReady]);

    useEffect(() => {
        if (charIndex < currentStepText.length) {
            const timeout = setTimeout(() => {
                setDisplayText(currentStepText.slice(0, charIndex + 1));
                setCharIndex(charIndex + 1);
            }, 30);
            return () => clearTimeout(timeout);
        }
    }, [charIndex, currentStepText]);

    return (
        <div className="w-full">
            <p className="text-sm text-gray-400 font-light tracking-wide">
                {displayText}
                {charIndex < currentStepText.length && (
                    <span className="animate-pulse">|</span>
                )}
            </p>
        </div>
    );
}
