export const ZaloIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="5" fill="#0068FF" />
    <text x="3" y="17" fontFamily="Arial, sans-serif" fontWeight="bold" fontSize="11" fill="white">Zalo</text>
  </svg>
);

/** Microsoft Teams icon (Bot Framework). */
export const TeamsIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#6264A7" />
    {/* Large person (foreground) */}
    <circle cx="13.5" cy="7.5" r="2.5" fill="white" />
    <path d="M8.5 19v-1.5C8.5 15.015 10.515 13 13 13h1c2.485 0 4.5 2.015 4.5 4.5V19H8.5z" fill="white" />
    {/* Small person (background, partially hidden) */}
    <circle cx="8" cy="8" r="1.8" fill="rgba(255,255,255,0.6)" />
    <path d="M4 18v-1C4 15.343 5.343 14 7 14h1.5C8.185 14.6 8 15.282 8 16v2H4v0z" fill="rgba(255,255,255,0.6)" />
  </svg>
);

export const FeishuIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="5" fill="#336FFF" />
    <path
      d="M8 17.5C9.5 15 11 13 12 11.5C13 13 14.5 15 16 17.5H13.5C13 16 12.7 15 12 13.8C11.3 15 11 16 10.5 17.5H8Z"
      fill="white"
    />
    <path
      d="M12 6.5C10.5 6.5 9.5 7.5 9.5 9C9.5 10.5 10.5 11.5 12 11.5C13.5 11.5 14.5 10.5 14.5 9C14.5 7.5 13.5 6.5 12 6.5Z"
      fill="white"
    />
  </svg>
);

export function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-3 w-3 flex-shrink-0 text-claude-text-muted transition-transform ${open ? "rotate-90" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
}

export function FolderIcon({ open }: { open: boolean }) {
  return open ? (
    <svg className="h-4 w-4 flex-shrink-0 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v1H2V6z" />
      <path fillRule="evenodd" d="M2 9h16l-1.5 6H3.5L2 9z" clipRule="evenodd" />
    </svg>
  ) : (
    <svg className="h-4 w-4 flex-shrink-0 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  );
}

export function FileIcon({ name }: { name: string }) {
  const ext = name.split(".").pop() ?? "";
  const color =
    ext === "md" ? "text-blue-400" : ext === "json" ? "text-yellow-500" : ext === "sh" ? "text-green-500" : "text-claude-text-muted";
  return (
    <svg className={`h-4 w-4 flex-shrink-0 ${color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}
