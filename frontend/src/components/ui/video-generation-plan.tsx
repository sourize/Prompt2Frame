"use client";

import React from "react";
import { TextShimmer } from "@/components/ui/text-shimmer";

interface VideoGenerationPlanProps {
    currentStep: number; // 0 = expanding, 1 = generating, 2 = rendering, 3 = completed
    isVideoReady?: boolean;
}

export default function VideoGenerationPlan({
    currentStep = 0,
    isVideoReady = false
}: VideoGenerationPlanProps) {
    const steps = [
        "Analyzing your prompt...",
        "Expanding prompt requirements...",
        "Generating Manim code...",
        "Rendering animation...",
    ];

    const currentStepText = isVideoReady ? "Video ready!" : (steps[currentStep] || steps[0]);

    // Use a lighter base color for the shimmer to be visible against dark background
    return (
        <div className="w-full">
            <TextShimmer
                className="text-sm font-light tracking-wide [--base-color:theme(colors.gray.400)] [--base-gradient-color:theme(colors.white)] dark:[--base-color:theme(colors.gray.400)] dark:[--base-gradient-color:theme(colors.white)]"
                duration={1.5}
            >
                {currentStepText}
            </TextShimmer>
        </div>
    );
}
