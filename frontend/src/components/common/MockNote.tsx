export function MockNote({ children }: { children?: React.ReactNode }) {
  return <p className="note small" role="note">{children ?? "Dữ liệu minh họa"}</p>;
}
