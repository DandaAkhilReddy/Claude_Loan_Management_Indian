import { useTranslation } from "react-i18next";
import { Menu, LogOut } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useUIStore } from "../../store/uiStore";
import { useLanguageStore } from "../../store/languageStore";

const languages = [
  { code: "en", label: "EN" },
  { code: "hi", label: "हिन्दी" },
  { code: "te", label: "తెలుగు" },
];

export function Header() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { toggleSidebar } = useUIStore();
  const { language, setLanguage } = useLanguageStore();

  return (
    <header className="h-16 sticky top-0 z-50 bg-white border-b border-gray-200 px-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button onClick={toggleSidebar} className="p-2 rounded-lg hover:bg-gray-100 md:block hidden">
          <Menu className="w-5 h-5 text-gray-600" />
        </button>
        <h1 className="text-lg font-bold text-gray-900">{t("app.title")}</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Language switcher */}
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => setLanguage(lang.code)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                language === lang.code
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>

        {/* User avatar / logout */}
        {user && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-medium text-blue-700">
              {(user.displayName?.[0] || user.email?.[0] || "U").toUpperCase()}
            </div>
            <button onClick={logout} className="p-2 rounded-lg hover:bg-gray-100" title={t("nav.logout")}>
              <LogOut className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
