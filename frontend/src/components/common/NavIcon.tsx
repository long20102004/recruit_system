/** Icon nét (24×24, stroke) cho menu sidebar; tên ứng với khoá menu trong RecruiterLayout. */
const PATHS: Record<string, string[]> = {
  home: ["M3 3h7v9H3z", "M14 3h7v5h-7z", "M14 12h7v9h-7z", "M3 16h7v5H3z"],
  adminHome: ["M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z", "M13.4 10.6 19 5", "M3.5 18a9 9 0 1 1 17 0"],
  jobs: ["M3 7h18v13H3z", "M8 7V4h8v3", "M3 12h18"],
  adminJobs: ["M3 7h18v13H3z", "M8 7V4h8v3", "M3 12h18"],
  candidates: ["M22 12h-6l-2 3h-4l-2-3H2", "M5.5 5h13L22 12v7H2v-7z"],
  matching: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z", "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"],
  interviewResults: ["M9 4h6v3H9z", "M15 5h3v16H6V5h3", "m9 14 2 2 4-4"],
  interviews: ["M4 19V5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z", "M4 19a2 2 0 0 0 2 2h14", "M9 7h7", "M9 11h5"],
  questions: ["M4 19V5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z", "M4 19a2 2 0 0 0 2 2h14", "M9 7h7", "M9 11h5"],
  cvSearch: ["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "m21 21-4.3-4.3"],
  company: ["M4 21V4h10v17", "M14 9h6v12", "M8 8h2", "M8 12h2", "M8 16h2", "M2 21h20"],
  companies: ["M4 21V4h10v17", "M14 9h6v12", "M2 21h20", "m7 12 2 2 3-4"],
  team: ["M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M2 21v-1a6 6 0 0 1 12 0v1", "M16 3.5a4 4 0 0 1 0 7", "M22 21v-1a6 6 0 0 0-4-5.6"],
  users: ["M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M4 21v-1a7 7 0 0 1 16 0v1"],
  roles: ["M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z", "m9 12 2 2 4-4"],
  templates: ["M3 3h18v18H3z", "M3 9h18", "M9 9v12"],
  notifications: ["M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9", "M10.3 21a1.94 1.94 0 0 0 3.4 0"],
  publicJobs: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M3 12h18", "M12 3a14 14 0 0 1 0 18", "M12 3a14 14 0 0 0 0 18"],
};

export function NavIcon({ name }: { name: string }) {
  const paths = PATHS[name] ?? PATHS.home;
  return (
    <svg className="sn-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths.map((d) => <path key={d} d={d} />)}
    </svg>
  );
}
