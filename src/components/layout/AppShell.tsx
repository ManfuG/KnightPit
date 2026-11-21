import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { Icon, type IconName } from "../ui/Icon";

export const PRODUCT_NAME = "Knight Pit";

type NavigationItem = {
  to: string;
  label: string;
  icon: IconName;
};

const navigation: NavigationItem[] = [
  { to: "/", label: "Home", icon: "board" },
  { to: "/play", label: "Play", icon: "play" },
  { to: "/training", label: "Training Board", icon: "target" },
  { to: "/history", label: "History", icon: "history" },
];

function Brand() {
  return (
    <NavLink to="/" className="brand" aria-label={`${PRODUCT_NAME} home`}>
      <img className="brand-mark" src={`${import.meta.env.BASE_URL}favicon.svg`} width="35" height="35" alt="" />
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
  return (
    <div className="app-background">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="shell">
        <aside className="sidebar" aria-label={`${PRODUCT_NAME} sidebar`}>
          <Brand />
          <Navigation />
          <a className="nav-link suite-link" href="https://giacomo-manfucci.pages.dev/pitverse/">← PitVerse</a>
        </aside>

        <div className="main-area">
          <header className="header-mobile">
            <Brand />
            <a className="nav-link suite-link" href="https://giacomo-manfucci.pages.dev/pitverse/">← PitVerse</a>
          </header>
          <main id="main-content" className="main-inner" tabIndex={-1}>
            <div>{children}</div>
          </main>
          <Navigation mobile />
        </div>
      </div>
    </div>
  );
}
