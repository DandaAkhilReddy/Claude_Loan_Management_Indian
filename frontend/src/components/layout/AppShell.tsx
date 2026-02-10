import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { MobileNav } from "./MobileNav";
import { ChatBot } from "../chat/ChatBot";
import { useUIStore } from "../../store/uiStore";

export function AppShell() {
  const { sidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="flex">
        {/* Desktop sidebar */}
        <div className={`hidden md:block ${sidebarOpen ? "w-64" : "w-0"} transition-all duration-200`}>
          {sidebarOpen && <Sidebar />}
        </div>
        {/* Main content */}
        <main className="flex-1 p-4 md:p-6 pb-20 md:pb-6">
          <Outlet />
        </main>
      </div>
      {/* Mobile bottom nav */}
      <MobileNav />
      {/* AI Chatbot */}
      <ChatBot />
    </div>
  );
}
