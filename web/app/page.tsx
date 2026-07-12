const stats = [
  { label: "Active signal", value: "99.9%" },
  { label: "Response layer", value: "12ms" },
  { label: "Grid uptime", value: "24/7" },
];

const capabilities = [
  {
    eyebrow: "01",
    title: "Neon Brand System",
    body: "A cinematic visual identity built from red pulse lines, green command states, and industrial gray panels.",
  },
  {
    eyebrow: "02",
    title: "Security-Led Presence",
    body: "Sharp sections for cyber teams, automation products, AI tools, launch pages, and operator-grade services.",
  },
  {
    eyebrow: "03",
    title: "Conversion Console",
    body: "Clear action zones, scan-friendly copy, and contact points designed for fast trust and fast decisions.",
  },
  {
    eyebrow: "04",
    title: "Hosted Launch Ready",
    body: "Built as a production-ready web experience with responsive motion, metadata, and deployable structure.",
  },
];

const systems = [
  "Identity lock",
  "Signal routing",
  "Threat surface",
  "AI workflow",
  "Launch hosting",
  "Ops dashboard",
];

const timeline = [
  {
    step: "Design",
    text: "Forge a red, green, and gray cyberpunk interface with strong hierarchy.",
  },
  {
    step: "Build",
    text: "Shape the first screen into a usable product site, not a placeholder.",
  },
  {
    step: "Publish",
    text: "Package the validated source and push it live as a hosted project.",
  },
];

export default function Home() {
  return (
    <main className="site-shell">
      <div className="grid-glow" aria-hidden="true" />
      <div className="scanline" aria-hidden="true" />

      <header className="nav-bar" aria-label="Primary navigation">
        <a className="brand-lockup" href="#top" aria-label="Chhoti Don home">
          <span className="brand-mark">CD</span>
          <span>Chhoti Don</span>
        </a>
        <nav className="nav-links" aria-label="Site sections">
          <a href="#systems">Systems</a>
          <a href="#work">Work</a>
          <a href="#contact">Contact</a>
        </nav>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Red Green Gray Cyber Grid</p>
          <h1>Chhoti Don Cyberpunk Command Website</h1>
          <p className="hero-lede">
            A high-impact digital command deck for AI, security, automation,
            and launch teams that need a bold online signal.
          </p>
          <div className="hero-actions" aria-label="Primary actions">
            <a className="button button-primary" href="#contact">
              Initiate Link
            </a>
            <a className="button button-secondary" href="#systems">
              View Systems
            </a>
          </div>
        </div>

        <div className="hero-visual" aria-label="Cyberpunk command preview">
          <img
            src="/og.png"
            alt="Red and green cyberpunk command city for Chhoti Don"
            className="hero-image"
          />
          <div className="terminal-panel">
            <span className="terminal-label">SYSTEM STATUS</span>
            <strong>ONLINE</strong>
            <span className="terminal-line">route: neon-sector-07</span>
            <span className="terminal-line">mode: hosted-production</span>
          </div>
        </div>
      </section>

      <section className="stat-strip" aria-label="Website performance signals">
        {stats.map((stat) => (
          <div className="stat" key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </div>
        ))}
      </section>

      <section className="section-block" id="systems">
        <div className="section-heading">
          <p className="eyebrow">Signal Stack</p>
          <h2>Built like a cyber command room.</h2>
        </div>
        <div className="capability-grid">
          {capabilities.map((item) => (
            <article className="capability-card" key={item.title}>
              <span>{item.eyebrow}</span>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="split-section" id="work">
        <div className="radar-board">
          <div className="radar-core" aria-hidden="true" />
          <div className="system-list">
            {systems.map((system) => (
              <span key={system}>{system}</span>
            ))}
          </div>
        </div>
        <div className="operations-copy">
          <p className="eyebrow">Operator Flow</p>
          <h2>From first impression to hosted launch.</h2>
          <div className="timeline">
            {timeline.map((item) => (
              <article className="timeline-item" key={item.step}>
                <strong>{item.step}</strong>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="final-cta" id="contact">
        <p className="eyebrow">Transmission Ready</p>
        <h2>Deploy the signal. Own the grid.</h2>
        <p>
          A polished cyberpunk website is ready to act as your brand front
          door, launch page, and hosted proof of work.
        </p>
        <a className="button button-primary" href="mailto:hello@chhotidon.local">
          Start Project
        </a>
      </section>
    </main>
  );
}
