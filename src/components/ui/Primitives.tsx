import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { Icon, type IconName } from "./Icon";

type ButtonVariant = "primary" | "secondary" | "ghost" | "quiet";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: IconName;
};

export function Button({ variant = "secondary", icon, className = "", children, ...props }: ButtonProps) {
  return (
    <button className={`button button-${variant} ${className}`} {...props}>
      {children}
      {icon && <Icon name={icon} width={16} height={16} />}
    </button>
  );
}

type LinkButtonProps = {
  to: string;
  variant?: ButtonVariant;
  icon?: IconName;
  children: ReactNode;
  className?: string;
};

export function LinkButton({ to, variant = "secondary", icon, children, className = "" }: LinkButtonProps) {
  return (
    <Link to={to} className={`button button-${variant} ${className}`}>
      {children}
      {icon && <Icon name={icon} width={16} height={16} />}
    </Link>
  );
}

type PanelProps = {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "aside";
};

export function Panel({ children, className = "", as = "div" }: PanelProps) {
  const Component = as;
  return <Component className={`panel ${className}`}>{children}</Component>;
}

type BadgeProps = {
  children: ReactNode;
  tone?: "muted" | "emerald" | "gold";
};

export function Badge({ children, tone = "muted" }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

type SectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function SectionHeading({ eyebrow, title, description, action }: SectionHeadingProps) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && <p className="section-description">{description}</p>}
      </div>
      {action}
    </div>
  );
}
