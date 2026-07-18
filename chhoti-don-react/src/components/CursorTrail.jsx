import React, { useEffect, useRef, useState } from 'react';

const DOT_COUNT = 7;

function computeCapable() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  // Only a real mouse-like pointer that can hover gets the custom cursor.
  return window.matchMedia('(pointer: fine)').matches && window.matchMedia('(hover: hover)').matches;
}

function osReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

/**
 * Premium cursor trail. It is shown ONLY when it can be shown safely:
 * a fine, hovering pointer, motion allowed, and no modal open. It adds the
 * `custom-cursor` class to <html> (which is what hides the native cursor) only
 * while it is genuinely active — and always removes it on cleanup — so the
 * native cursor can never be left invisible.
 */
export default function CursorTrail({ reduceMotion = false, suppressed = false }) {
  const target = useRef({ x: -100, y: -100 });
  const [points, setPoints] = useState(() =>
    Array.from({ length: DOT_COUNT }, () => ({ x: -100, y: -100 })),
  );
  const [capable, setCapable] = useState(computeCapable);
  const [osReduced, setOsReduced] = useState(osReducedMotion);

  // Re-evaluate device capability / motion preference if they change.
  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const mqs = [
      window.matchMedia('(pointer: fine)'),
      window.matchMedia('(hover: hover)'),
      window.matchMedia('(prefers-reduced-motion: reduce)'),
    ];
    const update = () => {
      setCapable(computeCapable());
      setOsReduced(osReducedMotion());
    };
    mqs.forEach((m) => m.addEventListener?.('change', update));
    return () => mqs.forEach((m) => m.removeEventListener?.('change', update));
  }, []);

  const active = capable && !reduceMotion && !osReduced && !suppressed;

  // The `custom-cursor` class (which hides the native cursor) is present ONLY
  // while the custom cursor is active. Cleanup always removes it.
  useEffect(() => {
    const html = document.documentElement;
    html.classList.toggle('custom-cursor', active);
    return () => html.classList.remove('custom-cursor');
  }, [active]);

  // Track the pointer and animate the trail only while active.
  useEffect(() => {
    if (!active) return undefined;
    const handleMove = (event) => {
      target.current = { x: event.clientX, y: event.clientY };
    };
    let frame;
    const animate = () => {
      setPoints((previous) => {
        const next = previous.map((point) => ({ ...point }));
        next[0].x += (target.current.x - next[0].x) * 0.28;
        next[0].y += (target.current.y - next[0].y) * 0.28;
        for (let index = 1; index < next.length; index += 1) {
          next[index].x += (next[index - 1].x - next[index].x) * 0.22;
          next[index].y += (next[index - 1].y - next[index].y) * 0.22;
        }
        return next;
      });
      frame = requestAnimationFrame(animate);
    };
    window.addEventListener('mousemove', handleMove, { passive: true });
    frame = requestAnimationFrame(animate);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      cancelAnimationFrame(frame);
    };
  }, [active]);

  if (!active) return null;

  // z-[200] keeps it above every UI layer (modals are z-[150]); it is also
  // suppressed entirely while a modal is open (see `suppressed`).
  return (
    <div className="pointer-events-none fixed inset-0 z-[200]" aria-hidden="true">
      {points.map((point, index) => {
        const size = Math.max(4, 18 - index * 2.1);
        return (
          <span
            key={index}
            className={index === 0 ? 'cursor-core' : 'cursor-trail-dot'}
            style={{
              width: size,
              height: size,
              opacity: Math.max(0.08, 0.62 - index * 0.08),
              transform: `translate3d(${point.x - size / 2}px, ${point.y - size / 2}px, 0)`,
            }}
          />
        );
      })}
    </div>
  );
}
