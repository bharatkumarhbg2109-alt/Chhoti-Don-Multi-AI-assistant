import React, { useEffect, useRef, useState } from 'react';

const DOT_COUNT = 7;

export default function CursorTrail() {
  const target = useRef({ x: -100, y: -100 });
  const [points, setPoints] = useState(() =>
    Array.from({ length: DOT_COUNT }, () => ({ x: -100, y: -100 })),
  );

  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return undefined;

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
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-[100] hidden md:block" aria-hidden="true">
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
