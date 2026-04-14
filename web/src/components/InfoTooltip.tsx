export function InfoTooltip({ text }: { text: string }) {
  return (
    <button className="info-i" aria-label="More info" tabIndex={0}>
      i<span className="tt">{text}</span>
    </button>
  );
}
