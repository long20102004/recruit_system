import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Dùng chung file .env ở gốc repo (chỉ biến có tiền tố VITE_ được đưa ra trình duyệt)
  envDir: "..",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
