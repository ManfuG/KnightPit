import type { ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { NavLink, useLocation } from "react-router-dom";
import { Icon, type IconName } from "../ui/Icon";

export const PRODUCT_NAME = "Knight Pit";

type NavigationItem = {
  to: string;
  label: string;
  icon: IconName;
};

const navigation: NavigationItem[] = [
  { to: "/", label: "Home", icon: "spark" },
  { to: "/play", label: "Play", icon: "play" },
  { to: "/training", label: "Training Board", icon: "board" },
  { to: "/history", label: "History", icon: "history" },
];

function Brand() {
  return (
    <NavLink to="/" className="brand" aria-label={`${PRODUCT_NAME} home`}>
      <span className="brand-mark"><Icon name="spark" width={17} height={17} /></span>
      <span className="brand-name">{PRODUCT_NAME}</span>
    </NavLink>
  );
}

function Navigation({ mobile = false }: { mobile?: boolean }) {
  return (
    <nav className={mobile ? "mobile-nav" : "primary-nav"} aria-label={mobile ? "Mobile navigation" : "Primary navigation"}>
      {navigation.map((item) => (
        <NavLink key={item.to} to={item.to} className="nav-link" end={item.to === "/"}>
          <Icon name={item.icon} width={18} height={18} />
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();

  return (
    <div className="app-background">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="shell">
        <aside className="sidebar" aria-label={`${PRODUCT_NAME} sidebar`}>
          <Brand />
          <p className="brand-subtitle">A focused chess atelier</p>
          <p className="nav-label">Workspace</p>
          <Navigation />
        </aside>

        <div className="main-area">
          <header className="header-mobile">
            <Brand />
          </header>
          <main id="main-content" className="main-inner" tabIndex={-1}>
            <motion.div
              key={location.pathname}
              initial={shouldReduceMotion ? false : { opacity: 0, y: 7 }}
              animate={{ opacity: 1, y: 0 }}
              transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.3, ease: "easeOut" }}
            >
              {children}
            </motion.div>
          </main>
          <Navigation mobile />
        </div>
      </div>
    </div>
  );
}
