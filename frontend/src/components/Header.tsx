import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useState } from "react";

const Header = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="fixed top-0 right-0 z-50 p-6">
      <div className="flex gap-3">
        <Button
          className="bg-white text-black hover:bg-gray-100 transition-all duration-200 font-medium"
          onClick={() => setIsOpen(true)}
        >
          Note
        </Button>
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Important Note</DialogTitle>
          </DialogHeader>
          <div className="mt-4 text-sm text-gray-600">
            <p>The backend runs on a free-tier serverless instance with strict resource limits.</p>
            <ul className="list-disc list-inside mt-3 space-y-2">
              <li><strong>Concurrency Limit:</strong> Only 1-2 users can generate at the same time.</li>
              <li><strong>"Too Many Requests":</strong> If you see this, the server is busy. Please wait 10-15 seconds and try again.</li>
              <li><strong>Generation Failures:</strong> Sometimes the AI generates complex code that times out. Try a simpler prompt.</li>
            </ul>
            <p className="mt-4 text-xs text-gray-400">Thank you for your patience with this demo!</p>
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
};

export default Header;
