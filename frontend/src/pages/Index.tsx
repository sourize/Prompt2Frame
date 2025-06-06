import Header from "@/components/Header";
import SearchInterface from "@/components/SearchInterface";
import { Github, Globe } from "lucide-react";

const Index = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  return (
    <div className="flex flex-col min-h-screen bg-black text-white overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-gray-900 via-black to-gray-900"></div>
      
      {/* Subtle pattern overlay */}
      <div 
        className="fixed inset-0 opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0)`,
          backgroundSize: '24px 24px'
        }}
      ></div>
      
      <div className="relative z-10 flex-1">
        <Header />
        <SearchInterface loading={loading} setLoading={setLoading} />
      </div>

      {/* Premium Footer */}
      <footer className="relative z-10 mt-auto border-t border-gray-800/50 bg-black/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-2">
              <span className="text-2xl">❤️</span>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-200">Built by Sourish</span>
                <span className="text-xs text-gray-400">Crafting digital experiences</span>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <a
                href="https://github.com/sourize"
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-2 text-gray-400 hover:text-white transition-colors duration-200"
              >
                <Github className="w-5 h-5" />
                <span className="text-sm font-medium">GitHub</span>
                <span className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 -translate-y-6 text-xs text-gray-400">
                  Check out my code
                </span>
              </a>
              <a
                href="https://sourish.xyz"
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-2 text-gray-400 hover:text-white transition-colors duration-200"
              >
                <Globe className="w-5 h-5" />
                <span className="text-sm font-medium">Portfolio</span>
                <span className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 -translate-y-6 text-xs text-gray-400">
                  Visit my website
                </span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
