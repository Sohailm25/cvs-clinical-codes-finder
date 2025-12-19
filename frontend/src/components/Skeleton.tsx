// ABOUTME: Skeleton loading components for smooth loading states.
// ABOUTME: Matches the shape of actual content for seamless transitions.

export function SkeletonResultCard() {
  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-xl overflow-hidden shadow-theme-sm animate-pulse">
      {/* System header skeleton */}
      <div className="px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-[var(--border-default)] rounded" />
            <div className="w-24 h-4 bg-[var(--border-default)] rounded" />
          </div>
          <div className="w-16 h-5 bg-[var(--border-default)] rounded-full" />
        </div>
      </div>

      {/* Results skeleton */}
      <div className="divide-y divide-[var(--border-subtle)]">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-start gap-3 p-4">
            <div className="w-8 h-8 bg-[var(--border-default)] rounded-lg flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="w-24 h-4 bg-[var(--border-default)] rounded" />
              <div className="w-48 h-3 bg-[var(--border-default)] rounded" />
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 bg-[var(--border-default)] rounded-full" />
                <div className="w-8 h-3 bg-[var(--border-default)] rounded" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonLoading() {
  return (
    <div className="space-y-4">
      {/* Summary skeleton */}
      <div className="space-y-2 animate-pulse">
        <div className="w-3/4 h-4 bg-[var(--border-default)] rounded" />
        <div className="w-full h-4 bg-[var(--border-default)] rounded" />
        <div className="w-2/3 h-4 bg-[var(--border-default)] rounded" />
      </div>

      {/* Result cards skeleton */}
      <SkeletonResultCard />
      <SkeletonResultCard />
    </div>
  );
}
