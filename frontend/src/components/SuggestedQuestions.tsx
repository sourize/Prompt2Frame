
import { Button } from "@/components/ui/button";
import { Globe, Car, Play, Link } from "lucide-react";

interface SuggestedQuestionsProps {
  onSuggestionClick: (suggestion: string) => void;
}

const SuggestedQuestions = ({ onSuggestionClick }: SuggestedQuestionsProps) => {
  const suggestions = [
    {
      icon: Globe,
      text: "Draw a red circle and transform it into a square",
      type: "geometric"
    },
    {
      icon: Car,
      text: "Create a bouncing ball that changes colors",
      type: "animation"
    },
    {
      icon: Play,
      text: "Animate a growing neural network visualization",
      type: "complex"
    },
    {
      icon: Link,
      text: "Make a simple pendulum swinging motion",
      type: "physics"
    }
  ];

  return (
    <div className="space-y-3">
      {suggestions.map((suggestion, index) => (
        <Button
          key={index}
          variant="ghost"
          onClick={() => onSuggestionClick(suggestion.text)}
          className="w-full justify-start text-left p-4 h-auto bg-gray-800/30 hover:bg-gray-700/50 border border-gray-700/30 rounded-xl transition-all duration-200 group"
        >
          <div className="flex items-center gap-3 w-full">
            <suggestion.icon className="w-4 h-4 text-gray-400 group-hover:text-gray-300 transition-colors duration-200 flex-shrink-0" />
            <span className="text-gray-300 group-hover:text-white transition-colors duration-200 text-sm">
              {suggestion.text}
            </span>
          </div>
        </Button>
      ))}
    </div>
  );
};

export default SuggestedQuestions;
