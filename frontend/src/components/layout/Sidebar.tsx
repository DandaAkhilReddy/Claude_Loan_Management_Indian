import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LayoutDashboard, Wallet, ScanLine, Zap, Calculator, Settings } from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, labelKey: "nav.dashboard" },
  { to: "/loans", icon: Wallet, labelKey: "nav.loans" },
  { to: "/scanner", icon: ScanLine, labelKey: "nav.scanner" },
  { to: "/optimizer", icon: Zap, labelKey: "nav.optimizer" },
  { to: "/emi-calculator", icon: Calculator, labelKey: "nav.emiCalculator" },
  { to: "/settings", icon: Settings, labelKey: "nav.settings" },
];

export function Sidebar() {
  const { t } = useTranslation();

  return (
    <aside className="h-[calc(100vh-64px)] sticky top-16 border-r border-gray-200 bg-white p-4">
      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            {t(item.labelKey)}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
