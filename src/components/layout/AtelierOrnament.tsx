import { useId } from "react";
import { useReducedMotion } from "motion/react";

export function AtelierOrnament({ className = "", orbiting = false }: { className?: string; orbiting?: boolean }) {
  const id = useId();
  const shouldReduceMotion = useReducedMotion();
  const animate = orbiting && !shouldReduceMotion;
  return (
    <svg className={`atelier-ornament ${className}`} viewBox="0 0 440 420" fill="none" aria-hidden="true" focusable="false">
      <g className="ornament-orbits">
        <path id={`${id}-outer`} d="M410 195a178 72 0 1 0-356 0a178 72 0 1 0 356 0" transform="rotate(-28 232 195)" />
        <path id={`${id}-middle`} d="M376 195a144 116 0 1 0-288 0a144 116 0 1 0 288 0" transform="rotate(36 232 195)" />
        <path id={`${id}-inner`} d="M323 195a91 91 0 1 0-182 0a91 91 0 1 0 182 0" />
        <path d="M232 87v216M124 195h216" strokeDasharray="2 9" />
      </g>
      <g className="ornament-leaves">
        <path d="M98 351c-31-8-52-34-48-67 30 4 48 29 48 67ZM112 320c-6-34 9-63 38-73 9 32-5 60-38 73ZM89 291c-32-1-54-22-56-52 30-2 52 20 56 52ZM124 269c-1-28 15-48 39-52 2 27-13 47-39 52ZM122 240c-25-10-36-31-29-54 25 8 38 30 29 54Z" />
      </g>
      <g className="ornament-stems">
        <path d="M65 393c55-64 6-88 59-159M97 350l-30-48M112 320l25-51M89 291l-39-40M124 269l27-37M122 240l-16-37" />
        <path d="M65 393c48-14 103-9 143 10" />
      </g>
      <g className="ornament-stars">
        {orbiting ? <>
          <g transform="rotate(-28 232 195)">
            <g transform={animate ? undefined : "translate(410 195)"}>
              <circle r="5" />
              {animate && <animateMotion dur="32s" begin="-7s" repeatCount="indefinite"><mpath href={`#${id}-outer`} /></animateMotion>}
            </g>
          </g>
          <g transform="rotate(36 232 195)">
            <g transform={animate ? undefined : "translate(232 79)"}>
              <circle r="7" />
              {animate && <animateMotion dur="26s" begin="-16s" repeatCount="indefinite"><mpath href={`#${id}-middle`} /></animateMotion>}
            </g>
          </g>
          <g transform={animate ? undefined : "translate(232 286)"}>
            <circle r="4" />
            {animate && <animateMotion dur="19s" begin="-4s" repeatCount="indefinite"><mpath href={`#${id}-inner`} /></animateMotion>}
          </g>
        </> : <>
          <circle cx="74" cy="207" r="5" />
          <circle cx="352" cy="109" r="7" />
          <circle cx="287" cy="266" r="4" />
        </>}
        <path d="m232 176 5 14 14 5-14 5-5 14-5-14-14-5 14-5ZM363 289l3 8 8 3-8 3-3 8-3-8-8-3 8-3ZM92 105l2 6 6 2-6 2-2 6-2-6-6-2 6-2Z" />
      </g>
      <g className="ornament-satellites">
        <circle cx="159" cy="96" r="4" />
        <circle cx="388" cy="225" r="3" />
        <circle cx="199" cy="342" r="3" />
        <path d="m316 47 18 14 27-5M345 354l21-17 26 6" />
        <circle cx="316" cy="47" r="2" />
        <circle cx="334" cy="61" r="2" />
        <circle cx="361" cy="56" r="2" />
        <circle cx="345" cy="354" r="2" />
        <circle cx="366" cy="337" r="2" />
        <circle cx="392" cy="343" r="2" />
      </g>
    </svg>
  );
}
