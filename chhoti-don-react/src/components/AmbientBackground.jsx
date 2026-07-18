import React from 'react';

export default function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_0%,#2a1029_0%,#120a18_34%,#08060d_72%,#040307_100%)]" />
      <div className="absolute -left-40 top-[-16%] h-[38rem] w-[38rem] rounded-full bg-rose-500/[0.11] blur-[135px]" />
      <div className="absolute right-[-15rem] top-[4%] h-[36rem] w-[36rem] rounded-full bg-fuchsia-600/[0.12] blur-[145px]" />
      <div className="absolute bottom-[-17rem] left-[26%] h-[38rem] w-[38rem] rounded-full bg-violet-600/[0.10] blur-[150px]" />
      <div className="absolute bottom-[4%] right-[16%] h-[18rem] w-[18rem] rounded-full bg-amber-300/[0.045] blur-[110px]" />
      <div className="absolute left-[12%] top-[20%] h-px w-[45%] rotate-[-14deg] bg-gradient-to-r from-transparent via-rose-300/10 to-transparent blur-[1px]" />
      <div className="absolute right-[3%] top-[62%] h-px w-[40%] rotate-[11deg] bg-gradient-to-r from-transparent via-fuchsia-300/10 to-transparent blur-[1px]" />
      <div className="absolute inset-0 bg-grid opacity-[0.11]" />
      <div className="absolute inset-0 noise-layer opacity-[0.03]" />
    </div>
  );
}
