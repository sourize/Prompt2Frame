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
            <p>The backend server can run only one instance at a time. If you get an error, there are 2 possibilities:</p>
            <ol className="list-decimal list-inside mt-2 space-y-1">
              <li>More than one user is accessing it</li>
              <li>The LLM's code is erroneous, causing the renderer service to fail in generating animations</li>
            </ol>
            <p className="mt-2">If you get an error, please try 2-3 times with a 5-7 second interval.</p>
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
};

export default Header;
