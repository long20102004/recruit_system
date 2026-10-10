# HireLens Frontend

React + Vite + TypeScript. Style và component chung **đồng bộ với** `ui-prototype`.

## Chạy

```bash
npm install
npm run dev
```

## Cấu trúc chung

```
src/
├── styles/main.css          # Copy 1:1 từ ui-prototype/assets/css/main.css
├── components/common/       # Component UI tái sử dụng
├── data/mockData.ts         # Mock tương đương mock-data.js
├── types/                   # Kiểu Job, Match, CV, Interview…
├── utils/                   # pct, filterJobs, role
└── context/ToastContext.tsx # Toast giống HireLens.toast
```

Import component:

```ts
import { Button, JobCard, SiteHeader, Page } from "./components/common";
```
