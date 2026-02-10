import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LayoutDashboard, PlusCircle, Settings } from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, labelKey: "nav.dashboard" },
  { to: "/scanner", icon: PlusCircle, labelKey: "nav.addLoan" },
  { to: "/settings", icon: Settings, labelKey: "nav.settings" },
];

export function MobileNav() {
  const { t } = useTranslation();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-2 py-1 z-50">
      <div className="flex justify-around">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center py-1.5 px-2 text-xs ${
                isActive ? "text-blue-600" : "text-gray-400"
              }`
            }
          >
            <item.icon className="w-5 h-5 mb-0.5" />
            <span className="truncate max-w-[56px]">{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
