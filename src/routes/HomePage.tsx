import { Link } from "react-router-dom";
import { Icon, type IconName } from "../components/ui/Icon";

const destinations: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/play", label: "Play", icon: "play" },
  { to: "/training", label: "Training Board", icon: "board" },
  { to: "/history", label: "History", icon: "history" },
];

export function HomePage() {
  return (
    <>
      <section className="hero">
        <h1>KnightPit</h1>
        <p className="hero-description">Offline chess with Stockfish, a training board, and your game history.</p>
      </section>

      <section aria-label="Workspace destinations">
        <div className="destination-grid">
          {destinations.map((destination) => (
            <Link key={destination.to} to={destination.to} className="destination-card">
              <span className="card-icon"><Icon name={destination.icon} width={22} height={22} /></span>
              <h2 className="card-title">{destination.label}</h2>
              <Icon className="card-arrow" name="arrow-up-right" width={18} height={18} />
            </Link>
          ))}
        </div>
      </section>
      <a className="licenses-link" href={`${import.meta.env.BASE_URL}THIRD_PARTY_LICENSES.txt`}>Licenses</a>
    </>
  );
}
