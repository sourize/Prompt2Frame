import Header from "@/components/Header";
import SearchInterface from "@/components/SearchInterface";
import { Github, Globe } from "lucide-react";

const Index = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  return (
    <div className="flex flex-col min-h-screen bg-black text-white overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-gray-900 via-black to-gray-900"></div>

      {/* Subtle grid pattern overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
          maskImage: 'radial-gradient(circle at center, black, transparent 80%)'
        }}
      ></div>

      <div className="relative z-10 flex-1">
        <Header />
        <SearchInterface loading={loading} setLoading={setLoading} />
      </div>

      {/* Footer */}
      <footer className="relative z-10 mt-auto border-t border-gray-800/50 bg-black/40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-4">
              <a href="https://github.com/sourize" target="_blank" rel="noopener noreferrer">
                <img
                  src="https://github.com/sourize.png"
                  alt="Sourish"
                  className="w-10 h-10 rounded-full border border-gray-700/50 hover:border-indigo-500/50 transition-colors"
                />
              </a>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-200">Built by Sourish</span>
                <span className="text-xs text-gray-500">Engineering 2D animations with AI</span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <a
                href="https://github.com/sourize/Prompt2Frame"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-400 hover:text-white transition-colors duration-200"
              >
                View Code
              </a>
              <a
                href="https://sourish.me"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-400 hover:text-white transition-colors duration-200"
              >
                Portfolio
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
