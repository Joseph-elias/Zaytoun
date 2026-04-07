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
        login: resolve(__dirname, "login.html"),
        signup: resolve(__dirname, "signup.html"),
        register: resolve(__dirname, "register.html"),
        myProfiles: resolve(__dirname, "my-profiles.html"),
        workers: resolve(__dirname, "workers.html"),
        market: resolve(__dirname, "market.html"),
        bookings: resolve(__dirname, "bookings.html"),
        oliveSeason: resolve(__dirname, "olive-season.html"),
        inventory: resolve(__dirname, "inventory.html"),
        insight: resolve(__dirname, "insight.html"),
      },
    },
  },
});


