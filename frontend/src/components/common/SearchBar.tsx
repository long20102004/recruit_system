import type { FormEvent, ReactNode } from "react";
import { Button } from "./Button";

interface SearchFieldProps {
  icon: ReactNode;
  children: ReactNode;
}

export function SearchField({ icon, children }: SearchFieldProps) {
  return (
    <div className="search-field">
      <span className="ico">{icon}</span>
      {children}
    </div>
  );
}

interface SearchBarProps {
  onSubmit?: (e: FormEvent<HTMLFormElement>) => void;
  keyword: string;
  onKeywordChange: (value: string) => void;
  city: string;
  onCityChange: (value: string) => void;
  keywordPlaceholder?: string;
  submitLabel?: string;
  cities?: { value: string; label: string }[];
}

const DEFAULT_CITIES = [
  { value: "TP. Hồ Chí Minh", label: "TP. Hồ Chí Minh" },
  { value: "Hà Nội", label: "Hà Nội" },
  { value: "Remote", label: "Remote" },
  { value: "all", label: "Toàn quốc" },
];

export function SearchBar({
  onSubmit,
  keyword,
  onKeywordChange,
  city,
  onCityChange,
  keywordPlaceholder = "Vị trí, kỹ năng, công ty…",
  submitLabel = "Tìm việc",
  cities = DEFAULT_CITIES,
}: SearchBarProps) {
  return (
    <form
      className="search-bar"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.(e);
      }}
    >
      <SearchField icon="V">
        <input
          type="search"
          placeholder={keywordPlaceholder}
          value={keyword}
          onChange={(e) => onKeywordChange(e.target.value)}
        />
      </SearchField>
      <SearchField icon="Đ">
        <select value={city} onChange={(e) => onCityChange(e.target.value)}>
          {cities.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </SearchField>
      <Button variant="primary" type="submit">
        {submitLabel}
      </Button>
    </form>
  );
}
