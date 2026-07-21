import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    fs: { strict: false },
    port: 5173,
    host: "0.0.0.0"
  },
  build: {
    charset: "utf8"
  },
  esbuild: {
    charset: "utf8"
  }
});
