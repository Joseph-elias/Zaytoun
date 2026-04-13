import { resolve } from "node:path";

import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        signup: resolve(__dirname, "signup.html"),
        forgotPassword: resolve(__dirname, "forgot-password.html"),
        register: resolve(__dirname, "register.html"),
        myProfiles: resolve(__dirname, "my-profiles.html"),
        settings: resolve(__dirname, "settings.html"),
        workers: resolve(__dirname, "workers.html"),
        market: resolve(__dirname, "market.html"),
        bookings: resolve(__dirname, "bookings.html"),
        oliveSeason: resolve(__dirname, "olive-season.html"),
        inventory: resolve(__dirname, "inventory.html"),
        insight: resolve(__dirname, "insight.html"),
        agroCopilot: resolve(__dirname, "agro-copilot.html"),
        consent: resolve(__dirname, "consent.html"),
        terms: resolve(__dirname, "terms.html"),
        privacy: resolve(__dirname, "privacy.html"),
      },
    },
  },
});

