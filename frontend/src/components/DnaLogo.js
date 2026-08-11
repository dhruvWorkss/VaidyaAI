import React from 'react';

/**
 * VaidyaAI mark — a double helix.
 *
 * The two strands are a half-period out of phase so they genuinely cross,
 * and the rungs sit at the widest points. The previous version used two
 * near-identical curves with varying opacity, which merged into a solid blob
 * below about 40px; this holds together down to 24px.
 */
export default function DnaLogo({ size = 32, spinning = false }) {
  const style = spinning
    ? {
        animation: 'dnaSpin 1.5s linear infinite',
        transformOrigin: 'center',
        display: 'block',
      }
    : { display: 'block' };

  return (
    <svg width={size} height={size} viewBox="0 0 32 32" style={style}>
      <circle cx="16" cy="16" r="15" fill="#16a34a" />

      <g stroke="#ffffff" strokeLinecap="round" fill="none">
        {/* Base pairs, drawn under the strands so the strands read as in front */}
        <g strokeWidth="2" opacity="0.95">
          <path d="M11.3 7.4 H20.7" />
          <path d="M10.5 16 H21.5" />
          <path d="M11.3 24.6 H20.7" />
        </g>

        {/* Strands — identical curves mirrored about the vertical axis */}
        <g strokeWidth="2.6">
          <path d="M10 4.5 C10 10, 22 11.5, 22 16 C22 20.5, 10 22, 10 27.5" />
          <path d="M22 4.5 C22 10, 10 11.5, 10 16 C10 20.5, 22 22, 22 27.5" />
        </g>
      </g>
    </svg>
  );
}
