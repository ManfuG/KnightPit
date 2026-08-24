import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "arrow-up-right"
  | "board"
  | "book"
  | "check"
  | "chevron-right"
  | "clock"
  | "history"
  | "menu"
  | "note"
  | "play"
  | "plus"
  | "sliders"
  | "spark"
  | "target";

type IconProps = SVGProps<SVGSVGElement> & {
  name: IconName;
};

const paths: Record<IconName, ReactNode> = {
  "arrow-up-right": <><path d="M6 18 18 6" /><path d="M8 6h10v10" /></>,
  board: <><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M4 10h16M10 4v16" /></>,
  book: <><path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H19v16H7.5A2.5 2.5 0 0 0 5 21z" /><path d="M5 5.5v15M9 7h6M9 11h6" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  "chevron-right": <path d="m9 5 7 7-7 7" />,
  clock: <><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></>,
  history: <><path d="M4 7v5h5" /><path d="M5.1 12a7 7 0 1 0 2-5" /><path d="M12 8v4l2.5 1.5" /></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  note: <><path d="M6 4h9l3 3v13H6z" /><path d="M14 4v4h4M9 12h6M9 16h4" /></>,
  play: <path d="m9 6 10 6-10 6z" />,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  sliders: <><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="8" cy="6" r="2" /><circle cx="16" cy="12" r="2" /><circle cx="10" cy="18" r="2" /></>,
  spark: <><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z" /><path d="m19 16 .6 2.4L22 19l-2.4.6L19 22l-.6-2.4L16 19l2.4-.6z" /></>,
  target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><path d="M12 2v3M22 12h-3M12 22v-3M2 12h3" /></>,
};

export function Icon({ name, width = 20, height = 20, fill = "none", stroke = "currentColor", strokeWidth = 1.7, ...props }: IconProps) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width={width} height={height} fill={fill} stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" {...props}>
      {paths[name]}
    </svg>
  );
}
