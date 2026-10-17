(function () {
  const ROLE_KEY = "hirelens_role";
  const JOBS_KEY = "hirelens_jobs_extra";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function getRole() {
    return localStorage.getItem(ROLE_KEY) || "candidate";
  }

  function setRole(role) {
    localStorage.setItem(ROLE_KEY, role);
  }

  function pct(n) {
    return Math.round(Number(n) * 100);
  }

  function toast(message) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2600);
  }

  function loadExtraJobs() {
    try {
      return JSON.parse(localStorage.getItem(JOBS_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveExtraJobs(jobs) {
    localStorage.setItem(JOBS_KEY, JSON.stringify(jobs));
  }

  /** Seed mock + tin recruiter đã đăng (localStorage). */
  function getJobs() {
    const base = window.HireLensMock.jobs || [];
    const extra = loadExtraJobs();
    const ids = new Set(extra.map((j) => j.id));
    return [...extra, ...base.filter((j) => !ids.has(j.id))];
  }

  function addJob(job) {
    const extra = loadExtraJobs();
    extra.unshift(job);
    saveExtraJobs(extra);
    return job;
  }

  function jobById(id) {
    return getJobs().find((j) => j.id === id);
  }

  function matchForJob(jobId) {
    return (window.HireLensMock.matchingResults || []).find((m) => m.jobId === jobId);
  }

  function logoFromCompany(name) {
    const parts = (name || "NW").trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  const LOGO_COLORS = ["#0d9488", "#2563eb", "#ea580c", "#059669", "#dc2626", "#7c3aed", "#0891b2"];

  function renderJobCard(job, options) {
    const opts = options || {};
    const match = matchForJob(job.id);
    const scoreHtml =
      opts.showMatch && match
        ? `<div class="match-badge">${pct(match.score)}% phù hợp</div>`
        : "";
    const near =
      job.nearYou && job.distanceKm != null
        ? `<span class="chip near">Cách bạn ~${job.distanceKm} km</span>`
        : job.nearYou
          ? `<span class="chip near">Gần bạn</span>`
          : "";
    const hot = job.hot ? `<span class="chip hot">Hot</span>` : "";

    return `
      <article class="job-card" data-job-id="${job.id}" style="animation-delay:${opts.delay || 0}ms">
        <div class="job-logo" style="background:${job.logoColor}">${job.logo}</div>
        <div>
          <h3>${job.title}</h3>
          <div class="job-meta">
            <span>${job.company}</span>
            <span>${job.location}</span>
            <span>${job.workType}</span>
            <span>${job.postedAgo}</span>
          </div>
          <div class="job-tags">
            ${hot}${near}
            <span class="chip brand">${job.level}</span>
            ${(job.requiredSkills || [])
              .slice(0, 3)
              .map((s) => `<span class="chip">${s}</span>`)
              .join("")}
          </div>
        </div>
        <div class="job-side">
          ${scoreHtml}
          <div class="salary">${job.salary}</div>
          <button class="btn btn-soft btn-sm" type="button" data-apply="${job.id}">Ứng tuyển</button>
        </div>
      </article>`;
  }

  function filterJobs({ keyword, city, nearOnly } = {}) {
    const kw = (keyword || "").trim().toLowerCase();
    return getJobs().filter((j) => {
      if (nearOnly && !j.nearYou) return false;
      if (city && city !== "all" && j.city !== city && !(city === "Remote" && j.city === "Remote")) {
        return false;
      }
      if (!kw) return true;
      const hay = [
        j.title,
        j.company,
        j.location,
        j.level,
        ...(j.requiredSkills || []),
        j.description || "",
        j.requirements || "",
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(kw);
    });
  }

  /**
   * @param {string} active key
   * @param {"public"|"candidate"|"recruiter"} mode
   */
  function renderHeader(active, mode) {
    const root = qs("[data-header]");
    if (!root) return;

    const role = getRole();
    const m = mode || (role === "recruiter" ? "recruiter" : "candidate");

    let links = [];
    let home = "index.html";
    let actions = "";

    if (m === "public") {
      home = "index.html";
      links = [
        { href: "index.html", key: "jobs", label: "Việc làm" },
        { href: "login.html", key: "login", label: "Đăng nhập" },
      ];
      actions = `
        <span class="loc-pill">Gần: ${HireLensMock.meta.userLocation}</span>
        <a class="btn btn-ghost btn-sm" href="login.html">Đăng nhập</a>
        <a class="btn btn-primary btn-sm" href="login.html">Tạo tài khoản</a>`;
    } else if (m === "recruiter") {
      home = "index.html";
      links = [
        { href: "index.html", key: "home", label: "Tổng quan" },
        { href: "jobs.html", key: "jobs", label: "Đăng tuyển" },
        { href: "candidates.html", key: "candidates", label: "Ứng viên" },
        { href: "matching.html", key: "matching", label: "Ghép hồ sơ" },
        { href: "interviews.html", key: "interviews", label: "Phỏng vấn" },
      ];
      actions = `
        <a class="btn btn-ghost btn-sm" href="../index.html">Trang chủ</a>
        <a class="btn btn-primary btn-sm" href="../login.html">Đổi vai trò</a>`;
    } else {
      home = "index.html";
      links = [
        { href: "index.html", key: "jobs", label: "Việc làm" },
        { href: "matching.html", key: "matching", label: "Phù hợp với tôi" },
        { href: "cv.html", key: "cv", label: "Hồ sơ / CV" },
        { href: "interview.html", key: "interview", label: "Phỏng vấn" },
      ];
      actions = `
        <span class="loc-pill">Gần: ${HireLensMock.meta.userLocation}</span>
        <a class="btn btn-ghost btn-sm" href="../index.html">Trang chủ</a>
        <a class="btn btn-primary btn-sm" href="../login.html">Đổi vai trò</a>`;
    }

    root.innerHTML = `
      <div class="site-header-inner">
        <a class="brand" href="${home}">
          <span class="brand-mark" aria-hidden="true"></span>
          HireLens
        </a>
        <nav class="nav-links">
          ${links
            .map(
              (l) =>
                `<a href="${l.href}" class="${active === l.key ? "active" : ""}">${l.label}</a>`
            )
            .join("")}
        </nav>
        <div class="header-actions">${actions}</div>
      </div>`;
  }

  function renderSidebar(active) {
    const role = getRole();
    renderHeader(active === "home" ? (role === "recruiter" ? "home" : "jobs") : active, role);
  }

  window.HireLens = {
    qs,
    qsa,
    getRole,
    setRole,
    pct,
    toast,
    getJobs,
    addJob,
    jobById,
    matchForJob,
    logoFromCompany,
    LOGO_COLORS,
    renderJobCard,
    filterJobs,
    renderHeader,
    renderSidebar,
  };
})();
