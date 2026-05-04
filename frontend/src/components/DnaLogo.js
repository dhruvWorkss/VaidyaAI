import React from 'react';

export default function DnaLogo({ size = 32, spinning = false }) {
  const spinStyle = spinning ? {
    animation: 'dnaSpin 1.5s linear infinite',
    transformOrigin: 'center',
    display: 'block',
  } : { display: 'block' };

  return (
    <svg width={size} height={size} viewBox="0 0 32 32" style={spinStyle}>
      <circle cx="16" cy="16" r="15" fill="#16a34a" />
      <path
        d="M12 4 C18 9 14 14 12 16 C10 18 14 23 12 28"
        fill="none"
        stroke="white"
        strokeWidth="2.2"
        strokeLinecap="round"
        style={spinning ? {
          strokeDasharray: '30',
          animation: 'dnaRotate 1s linear infinite',
        } : {}}
      />
      <path
        d="M20 4 C14 9 18 14 20 16 C22 18 18 23 20 28"
        fill="none"
        stroke="white"
        strokeWidth="2.2"
        strokeLinecap="round"
        opacity="0.75"
        style={spinning ? {
          strokeDasharray: '30',
          animation: 'dnaRotate 1s linear infinite reverse',
        } : {}}
      />
      <line x1="13" y1="9" x2="19" y2="9" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.9"/>
      <line x1="12" y1="16" x2="20" y2="16" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.9"/>
      <line x1="13" y1="23" x2="19" y2="23" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.9"/>
    </svg>
  );
}