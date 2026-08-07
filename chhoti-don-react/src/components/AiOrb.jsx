import React from 'react';

export default function AiOrb({ compact = false, thinking = false }) {
  const size = compact ? 'h-24 w-24 sm:h-28 sm:w-28' : 'h-36 w-36 sm:h-44 sm:w-44';

  return (
    <div
      className={`relative ${size} animate-orb-float`}
      aria-label={thinking ? 'Chhoti Don is thinking' : 'Chhoti Don is online'}
    >
      <div className="absolute inset-[-22%] rounded-full bg-brand-deep-500/[0.09] blur-3xl animate-pulse-soft" />
      <div className="absolute inset-[-11%] rounded-full border border-brand-300/20 animate-orb-spin">
        <span className="absolute left-1/2 top-[-4px] h-2 w-2 -translate-x-1/2 rounded-full bg-brand-200 shadow-[0_0_18px_rgba(107,163,190,.95)]" />
      </div>
      <div className="absolute inset-[-5%] rounded-full border border-brand-deep-300/10 animate-orb-spin-reverse">
        <span className="absolute bottom-[10%] right-[7%] h-1.5 w-1.5 rounded-full bg-brand-mist-200 shadow-[0_0_14px_rgba(253,230,138,.85)]" />
      </div>
      <div className="absolute inset-0 rounded-full border border-white/15 bg-white/[0.035] backdrop-blur-xl shadow-[inset_0_0_48px_rgba(255,255,255,.055),0_0_64px_rgba(10,112,117,.17)]" />
      <div className="absolute inset-[9%] overflow-hidden rounded-full border border-white/10 bg-[#032f30]/80 shadow-[inset_0_0_50px_rgba(3,23,22,.95)]">
        <div className="orb-liquid absolute -left-[15%] -top-[8%] h-[76%] w-[86%] rounded-[42%_58%_55%_45%/55%_38%_62%_45%] bg-gradient-to-br from-brand-300 via-brand-deep-500 to-brand-blue-700 opacity-95 blur-[1px]" />
        <div className="orb-liquid-two absolute -bottom-[18%] -right-[20%] h-[90%] w-[92%] rounded-[58%_42%_45%_55%/45%_63%_37%_55%] bg-gradient-to-tr from-brand-mist-200 via-brand-500 to-purple-700 opacity-75 mix-blend-screen" />
        <div className="absolute inset-[20%] rounded-full bg-white/20 blur-xl" />
        <div className="absolute left-[24%] top-[17%] h-[19%] w-[19%] rounded-full bg-brand-50/85 blur-[6px]" />
        <div className="absolute bottom-[19%] right-[20%] h-[8%] w-[8%] rounded-full bg-brand-mist-100/70 blur-[3px]" />
      </div>
      <div className="absolute inset-[2%] rounded-full border border-brand-blue-300/15 animate-orb-spin-reverse" />
      {thinking && (
        <>
          <div className="absolute inset-[-15%] rounded-full border border-brand-400/20 animate-ping-slow" />
          <div className="absolute inset-[-8%] rounded-full border border-brand-deep-400/20 animate-ping-slow [animation-delay:700ms]" />
        </>
      )}
    </div>
  );
}
