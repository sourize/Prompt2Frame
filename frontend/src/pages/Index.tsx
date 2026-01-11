import Header from "@/components/Header";
import SearchInterface from "@/components/SearchInterface";
import { Footer } from "@/components/ui/footer";
import { Github, Globe, Sparkles, Twitter } from "lucide-react";

const Index = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  return (
    <div className="flex flex-col min-h-screen bg-black text-white">
      {/* Background gradient */}
      {/* Background gradient removed */}

      {/* ... previous grid pattern code ... */}

      <div className="relative z-10 flex-1">
        <Header />
        <SearchInterface loading={loading} setLoading={setLoading} />
      </div>

      {/* Footer */}
      <div className="relative z-10">
        <Footer
          logo={<Sparkles className="h-6 w-6 text-indigo-400" />}
          brandName="Prompt2Frame"
          socialLinks={[
            {
              icon: <Github className="h-5 w-5" />,
              href: "https://github.com/sourize/Prompt2Frame",
              label: "GitHub",
            },
            {
              icon: <Twitter className="h-5 w-5" />,
              href: "https://x.com/sourize_",
              label: "Twitter",
            },
            {
              icon: <Globe className="h-5 w-5" />,
              href: "https://sourish.me",
              label: "Portfolio",
            },
          ]}
          mainLinks={[]}
          legalLinks={[
            { href: "#", label: "Privacy Policy" },
            { href: "#", label: "Terms of Service" },
          ]}
          copyright={{
            text: "© 2024 Sourish Chatterjee",
            license: "All rights reserved",
          }}
        />
      </div>
    </div>
  );
};

export default Index;
