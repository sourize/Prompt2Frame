import React from "react";

type FooterProps = { loading: boolean };
const Footer = ({ loading }: FooterProps) => {
  return (
    <footer className="fixed bottom-0 left-0 w-full py-6 flex flex-col items-center bg-transparent z-50">
      {loading && (
        <div className="mb-2 flex justify-center transition-opacity duration-500 opacity-100 animate-fade-in-out">
          <svg className="animate-spin h-6 w-6 text-pink-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      )}
      <div className="flex flex-col items-center gap-1">
        <span className="flex items-center gap-1 text-gray-200 text-sm font-medium">
          <span role="img" aria-label="heart" className="text-pink-500">❤️</span>
          Built by Sourish
        </span>
        <div className="flex gap-6 mt-1">
          <a
            href="https://github.com/sourize"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-200 hover:text-gray-300 text-sm transition-colors duration-200"
          >
            GitHub
          </a>
          <a
            href="https://sourish.xyz"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-200 hover:text-gray-300 text-sm transition-colors duration-200"
          >
            Portfolio
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer; 