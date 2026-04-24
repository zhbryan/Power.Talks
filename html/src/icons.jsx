// Simple inline stroke icons
const Icon = ({ d, size = 18, fill = "none", stroke = "currentColor", sw = 1.6, children, style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke}
    strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" style={style} aria-hidden>
    {d ? <path d={d} /> : children}
  </svg>
);

const I = {
  Logo: ({ size = 24 }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <defs>
        <linearGradient id="pt-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--accent)" />
          <stop offset="1" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14" fill="url(#pt-g)"/>
      <path d="M10 10v12M10 10h5a3.5 3.5 0 0 1 0 7h-5" stroke="#fff" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="22.5" cy="21" r="1.6" fill="#fff"/>
    </svg>
  ),
  Search:  (p) => <Icon {...p}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></Icon>,
  Plus:    (p) => <Icon {...p}><path d="M12 5v14M5 12h14"/></Icon>,
  Mic:     (p) => <Icon {...p}><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></Icon>,
  Send:    (p) => <Icon {...p}><path d="M4 12h14M14 6l6 6-6 6"/></Icon>,
  Attach:  (p) => <Icon {...p}><path d="M21 12.5 13 20.5a5 5 0 0 1-7-7l9-9a3.5 3.5 0 1 1 5 5l-8.5 8.5a2 2 0 1 1-3-3L16 8"/></Icon>,
  Sparkle: (p) => <Icon {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/></Icon>,
  Book:    (p) => <Icon {...p}><path d="M4 5a2 2 0 0 1 2-2h13v17H6a2 2 0 0 0-2 2V5zM19 18H6"/></Icon>,
  Chart:   (p) => <Icon {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></Icon>,
  Folder:  (p) => <Icon {...p}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/></Icon>,
  Gear:    (p) => <Icon {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></Icon>,
  ChevL:   (p) => <Icon {...p}><path d="m15 6-6 6 6 6"/></Icon>,
  ChevR:   (p) => <Icon {...p}><path d="m9 6 6 6-6 6"/></Icon>,
  ChevD:   (p) => <Icon {...p}><path d="m6 9 6 6 6-6"/></Icon>,
  Close:   (p) => <Icon {...p}><path d="M6 6l12 12M18 6 6 18"/></Icon>,
  Stage:   (p) => <Icon {...p}><path d="M3 20h18M6 20V9h12v11M9 9V5h6v4M12 13v4"/></Icon>,
  Clock:   (p) => <Icon {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></Icon>,
  Target:  (p) => <Icon {...p}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></Icon>,
  Flame:   (p) => <Icon {...p}><path d="M12 3c1 4 5 5 5 10a5 5 0 1 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3-1-3 0-6 1-9z"/></Icon>,
  Lightning:(p)=> <Icon {...p}><path d="M13 3 4 14h6l-1 7 9-11h-6l1-7z"/></Icon>,
  Waveform:(p) => <Icon {...p}><path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2M21 12h0"/></Icon>,
  User:    (p) => <Icon {...p}><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></Icon>,
  Copy:    (p) => <Icon {...p}><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></Icon>,
  Refresh: (p) => <Icon {...p}><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 4v4h-4M21 12a9 9 0 0 1-15 6.7L3 16M3 20v-4h4"/></Icon>,
  Thumbsup:(p) => <Icon {...p}><path d="M7 10v11H3V10h4zM7 10l5-7c1.5 0 2.5 1 2.5 2.5V9h5a2 2 0 0 1 2 2.3l-1.5 8A2 2 0 0 1 18 21H7"/></Icon>,
  Share:   (p) => <Icon {...p}><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 10.8 15.8 7.2M8.2 13.2l7.6 3.6"/></Icon>,
  Pin:     (p) => <Icon {...p}><path d="M12 17v4M9 3h6l-1 4 3 3v3H7v-3l3-3-1-4z"/></Icon>,
  Globe:   (p) => <Icon {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></Icon>,
  Bolt:    (p) => <Icon {...p}><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z"/></Icon>,
  Home:    (p) => <Icon {...p}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></Icon>,
};

window.I = I;
window.Icon = Icon;
