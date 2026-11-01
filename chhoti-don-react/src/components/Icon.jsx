import React from 'react';

const paths = {
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  plus: <path d="M12 5v14M5 12h14" />,
  sparkles: <path d="m12 3 1.3 3.7L17 8l-3.7 1.3L12 13l-1.3-3.7L7 8l3.7-1.3L12 3Zm6 10 .8 2.2L21 16l-2.2.8L18 19l-.8-2.2L15 16l2.2-.8L18 13ZM5 14l1 2.8L9 18l-3 1.2L5 22l-1-2.8L1 18l3-1.2L5 14Z" />,
  chat: <path d="M7 8h10M7 12h7m-9.5 7 2.8-2H18a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3v7a3 3 0 0 0 1.5 2.6V19Z" />,
  history: <path d="M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5m4-2v6l4 2" />,
  grid: <path d="M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z" />,
  brain: <path d="M9 4.5a3 3 0 0 0-5 2.2A3.5 3.5 0 0 0 5.5 13v1a3.5 3.5 0 0 0 3.5 3.5M15 4.5a3 3 0 0 1 5 2.2 3.5 3.5 0 0 1-1.5 6.3v1a3.5 3.5 0 0 1-3.5 3.5M9 4.5V20m6-15.5V20M9 9H6.5M15 9h2.5M9 14H6.5m8.5 0h2.5M9 20h6" />,
  settings: <path d="M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Zm7.2-3.2a6 6 0 0 0-.1-1l2-1.5-2-3.4-2.4 1a7.6 7.6 0 0 0-1.7-1L14.7 3h-4l-.4 3.1a7.6 7.6 0 0 0-1.7 1l-2.4-1-2 3.4 2 1.5a6 6 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a7.6 7.6 0 0 0 1.7 1l.4 3.1h4l.4-3.1a7.6 7.6 0 0 0 1.7-1l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z" />,
  search: <path d="m20 20-4.3-4.3m2.3-5.2a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" />,
  more: <path d="M5 12h.01M12 12h.01M19 12h.01" />,
  attachment: <path d="m8.5 12.5 6-6a3 3 0 0 1 4.2 4.2l-7.4 7.4a5 5 0 0 1-7.1-7.1l7.2-7.2" />,
  mic: <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Zm-7 9a7 7 0 0 0 14 0M12 19v3m-4 0h8" />,
  send: <path d="m4 4 17 8-17 8 3-8-3-8Zm3 8h14" />,
  shield: <path d="M12 3 5 6v5c0 4.8 2.9 8 7 10 4.1-2 7-5.2 7-10V6l-7-3Zm-3 9 2 2 4-4" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  copy: <path d="M9 9h10v10H9V9Zm-4 6H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" />,
  thumbsUp: <path d="M7 10v10H3V10h4Zm0 9h10.2a2 2 0 0 0 2-1.7l1-6A2 2 0 0 0 18.2 9H15l.7-3.2A2.3 2.3 0 0 0 11.3 5L8 10" />,
  volume: <path d="M5 10v4h3l4 4V6L8 10H5Zm10-1a4 4 0 0 1 0 6m2.5-8.5a8 8 0 0 1 0 11" />,
  logout: <path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5m5-4 4-4-4-4m4 4H9" />,
  sun: <path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4m0-12.8L17 7M7 17l-1.4 1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" />,
  moon: <path d="M20.7 15.2A8.6 8.6 0 0 1 8.8 3.3 8.8 8.8 0 1 0 20.7 15.2Z" />,
  cpu: <path d="M9 3v2m6-2v2M9 19v2m6-2v2M3 9h2m14 0h2M3 15h2m14 0h2M7 7h10v10H7V7Zm3 3h4v4h-4v-4Z" />,
  pulse: <path d="M3 12h4l2 6 4-14 2 8h6" />,
  terminal: <path d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm3 4 3 3-3 3m6 0h4" />,
  trash: <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7m4 4v6m4-6v6" />,
  edit: <path d="M4 20h4L18.5 9.5a2 2 0 0 0-2.8-2.8L5 17.2V20Zm10-11 2.5 2.5" />,
  stop: <path d="M8 8h8v8H8V8Z" />,
  database: <path d="M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3Zm8 3v6c0 1.7-3.6 3-8 3s-8-1.3-8-3V6m16 6v6c0 1.7-3.6 3-8 3s-8-1.3-8-3v-6" />,
  desktop: <path d="M4 4h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm4 16h8m-4-4v4" />,
  refresh: <path d="M4 4v5h5M20 20v-5h-5M20 9a8 8 0 0 0-14.9-2M4 15a8 8 0 0 0 14.9 2" />,
  code: <path d="m16 18 6-6-6-6M8 6l-6 6 6 6" />,
};

export default function Icon({ name, className = 'h-5 w-5', strokeWidth = 1.8 }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {paths[name] ?? paths.sparkles}
    </svg>
  );
}
