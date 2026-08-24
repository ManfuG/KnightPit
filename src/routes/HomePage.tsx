import { motion, useReducedMotion } from "motion/react";
import { Link } from "react-router-dom";
import { Icon, type IconName } from "../components/ui/Icon";

const destinations: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/play", label: "Play", icon: "play" },
  { to: "/training", label: "Training Board", icon: "board" },
  { to: "/history", label: "History", icon: "history" },
];

export function HomePage() {
  const shouldReduceMotion = useReducedMotion();

  return (
    <>
      <motion.section className="hero" initial={shouldReduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: shouldReduceMotion ? 0 : .45 }}>
        <h1>KnightPit</h1>
        <p className="hero-description">A local chess atelier for AI play, position training, and replayable games. The CPU-only AI combines a compact policy/value network with Monte Carlo Tree Search, trained from its own self-play.</p>
      </motion.section>

      <section aria-label="Workspace destinations">
        <div className="destination-grid">
          {destinations.map((destination, index) => (
            <motion.div key={destination.to} initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: shouldReduceMotion ? 0 : .08 * index, duration: shouldReduceMotion ? 0 : .35 }}>
              <Link to={destination.to} className="panel destination-card">
                <span className="card-icon"><Icon name={destination.icon} width={19} height={19} /></span>
                <h3 className="card-title">{destination.label}</h3>
                <Icon className="card-arrow" name="arrow-up-right" width={16} height={16} />
              </Link>
            </motion.div>
          ))}
        </div>
      </section>
    </>
  );
}
