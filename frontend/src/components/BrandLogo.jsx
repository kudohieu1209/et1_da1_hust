export default function BrandLogo({ size = 36, decorative = false, style }) {
  return (
    <img
      src="/brand/hust-advisor-logo.png"
      alt={decorative ? '' : 'HUST Advisor'}
      width={size}
      height={size}
      draggable={false}
      style={{ display: 'block', objectFit: 'contain', flexShrink: 0, ...style }}
    />
  );
}
