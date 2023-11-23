import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    host: "::",
    port: 55140,
    proxy: {
      "/data_backend": {
        target: (process.env.data_backend_host || "http://127.0.0.1:55123"),
        changeOrigin: true,
        secure: false,
      },
      "/org": {
        target: (process.env.organization_backend_host || "http://127.0.0.1:55125"),
        changeOrigin: true,
        secure: false,
        //rewrite: (path) => path.replace(/^\/org/, '/'),
      },
      "/static": {
        target: (process.env.organization_backend_host || "http://127.0.0.1:55125"),
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [vue()],
  assetsInclude: ["**/*.vert", "**/*.frag", "src/textures/*.jpg"],
})
