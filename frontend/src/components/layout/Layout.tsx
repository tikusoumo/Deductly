import React from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      <Header />
      <div className="flex">
        <div className="hidden md:block border-r bg-white/30 backdrop-blur-sm">
          <Sidebar />
        </div>
        <main className="flex-1 p-6">
          <div className="mx-auto min-w-full">{children}</div>
        </main>
      </div>
    </div>
  );
};
