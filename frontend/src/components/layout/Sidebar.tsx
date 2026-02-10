import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LayoutDashboard, PlusCircle, Settings, MessageSquare, ShieldCheck } from "lucide-react";
import { useAuthStore } from "../../store/authStore";

const ADMIN_EMAILS = ["areddy@hhamedicine.com", "admin@test.com"];

const navItems = [
  { to: "/", icon: LayoutDashboard, labelKey: "nav.dashboard" },
  { to: "/scanner", icon: PlusCircle, labelKey: "nav.addLoan" },
  { to: "/feedback", icon: MessageSquare, labelKey: "nav.feedback" },
  { to: "/settings", icon: Settings, labelKey: "nav.settings" },
];

const adminItem = { to: "/admin", icon: ShieldCheck, labelKey: "nav.admin" };

export function Sidebar() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const isAdmin = ADMIN_EMAILS.includes(user?.email || "");

  const items = isAdmin ? [...navItems, adminItem] : navItems;

  return (
    <aside className="h-[calc(100vh-64px)] sticky top-16 border-r border-gray-200 bg-white p-4">
      <nav className="space-y-1">
        {items.map((item) => (
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
