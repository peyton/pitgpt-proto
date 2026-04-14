export function InfoTooltip({ text }: { text: string }) {
  return (
    <details className="info-i">
      <summary aria-label="More info">i</summary>
      <span className="tt" role="tooltip">{text}</span>
    </details>
  );
}
