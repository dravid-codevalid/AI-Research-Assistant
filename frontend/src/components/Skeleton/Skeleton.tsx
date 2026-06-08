import './Skeleton.css';

interface SkeletonProps {
  lines?: number;
  width?: 'full' | 'lg' | 'md' | 'sm';
}

const widthCycle: Array<'full' | 'lg' | 'md' | 'sm'> = ['full', 'lg', 'md', 'sm'];

export default function Skeleton({ lines = 3, width = 'full' }: SkeletonProps) {
  return (
    <div className="skeleton" role="status" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => {
        const w = width === 'full' ? widthCycle[i % widthCycle.length] : width;
        return (
          <div
            key={i}
            className={`skeleton__line skeleton__line--${w}`}
            style={{ animationDelay: `${i * 100}ms` }}
          />
        );
      })}
    </div>
  );
}
