export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="50 120 410 270">
      <defs>
        <linearGradient id="lg-a" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FF006E" />
          <stop offset="100%" stopColor="#FF4D94" />
        </linearGradient>
        <linearGradient id="lg-b" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FF4D94" />
          <stop offset="100%" stopColor="#FF80B5" />
        </linearGradient>
      </defs>
      <circle cx="200" cy="256" r="115" fill="url(#lg-a)" opacity=".9" />
      <circle cx="312" cy="256" r="115" fill="url(#lg-b)" opacity=".75" />
    </svg>
  );
}

export function LogoWordmark({ size = 20 }: { size?: number }) {
  return (
    <div className="sidebar-logo">
      <LogoMark size={size * 1.5} />
      <span>
        Pit<em>GPT</em>
      </span>
    </div>
  );
}
