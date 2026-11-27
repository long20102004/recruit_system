import { apiData } from "../client";

export type CompanyStatus = "ACTIVE" | "PENDING" | "REJECTED" | "LOCKED";

export interface CompanyLicenseFile {
  name: string;
  meta: string;
}

export interface CompanyDto {
  id: number;
  name: string;
  legalName: string;
  logo: string;
  industry: string;
  size: string;
  city: string;
  tagline: string;
  about: string;
  perks: string[];
  skills: string[];
  founded: number;
  website: string;
  workingDays: string;
  overtime: string;
  address: string;
  workMode: string;
  openJobsCount: number;
  status: CompanyStatus;
  submittedAt: string;
  submittedBy: string;
  taxCode: string;
  email: string;
  phone: string;
  rejectReason: string | null;
  licenseFile: CompanyLicenseFile;
  following?: boolean;
  followersCount?: number;
  /** URL công khai trên R2; null khi chưa tải ảnh (specs/008-r2-storage). */
  logoUrl?: string | null;
  coverUrl?: string | null;
}

export interface CompanyListFilter {
  status?: CompanyStatus | "ALL";
  q?: string;
  city?: string;
  industry?: string;
  sort?: string;
}

function normalizeCompany(raw: CompanyDto): CompanyDto {
  return {
    ...raw,
    legalName: raw.legalName || raw.name,
    tagline: raw.tagline || "",
    about: raw.about || "",
    perks: raw.perks ?? [],
    skills: raw.skills ?? [],
    founded: raw.founded ?? 0,
    website: raw.website || "",
    workingDays: raw.workingDays || "",
    overtime: raw.overtime || "",
    address: raw.address || "",
    workMode: raw.workMode || "",
    submittedAt: raw.submittedAt || "",
    submittedBy: raw.submittedBy || "",
    taxCode: raw.taxCode || "",
    email: raw.email || "",
    phone: raw.phone || "",
    licenseFile: raw.licenseFile ?? { name: "GPKD.pdf", meta: "" },
  };
}

export async function listCompanies(filter?: CompanyListFilter): Promise<CompanyDto[]> {
  const qs = new URLSearchParams();
  if (filter?.q?.trim()) qs.set("q", filter.q.trim());
  if (filter?.city && filter.city !== "all") qs.set("city", filter.city);
  if (filter?.industry && filter.industry !== "all") qs.set("industry", filter.industry);
  if (filter?.sort) qs.set("sort", filter.sort);

  const isAdminQuery = Boolean(filter?.status && filter.status !== "ACTIVE");
  if (isAdminQuery && filter?.status) {
    qs.set("status", filter.status);
  }
  const query = qs.toString() ? `?${qs.toString()}` : "";
  const path = isAdminQuery ? `/admin/companies${query}` : `/companies${query}`;
  const items = await apiData<CompanyDto[]>(path);
  return (items ?? []).map(normalizeCompany);
}

export async function getCompany(id: number): Promise<CompanyDto> {
  const item = await apiData<CompanyDto>(`/companies/${id}`);
  return normalizeCompany(item);
}

export async function followCompany(id: number): Promise<{ following: boolean; followersCount: number }> {
  return apiData<{ companyId: number; following: boolean; followersCount: number }>(`/companies/${id}/follow`, {
    method: "POST",
  });
}

export async function unfollowCompany(id: number): Promise<{ following: boolean; followersCount: number }> {
  return apiData<{ companyId: number; following: boolean; followersCount: number }>(`/companies/${id}/follow`, {
    method: "DELETE",
  });
}

export async function approveCompany(id: number): Promise<CompanyDto> {
  const item = await apiData<CompanyDto>(`/admin/companies/${id}/approve`, { method: "POST" });
  return normalizeCompany(item);
}

export async function rejectCompany(id: number, reason: string): Promise<CompanyDto> {
  const item = await apiData<CompanyDto>(`/admin/companies/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
  return normalizeCompany(item);
}

export async function lockCompany(id: number, reason?: string): Promise<CompanyDto> {
  const item = await apiData<CompanyDto>(`/admin/companies/${id}/lock`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? "" }),
  });
  return normalizeCompany(item);
}

export async function unlockCompany(id: number): Promise<CompanyDto> {
  const item = await apiData<CompanyDto>(`/admin/companies/${id}/unlock`, { method: "POST" });
  return normalizeCompany(item);
}
