import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    host: "::",
    port: 55140,
    proxy: {
      "/data_backend": {  // data-backend is now a part of the backend
        target: (process.env.backend_host || "http://127.0.0.1:55125"),
        changeOrigin: false,
        secure: false,
      },
      "/org": {  // allows the browser to access endpoints of the backend directly
        target: (process.env.backend_host || "http://127.0.0.1:55125"),
        changeOrigin: false,
        secure: false,
        //rewrite: (path) => path.replace(/^\/org/, '/'),
      },
      "/api": {  // allows the browser to access endpoints of the backend directly
        target: (process.env.backend_host || "http://127.0.0.1:55125"),
        changeOrigin: false,
        secure: false,
        //rewrite: (path) => path.replace(/^\/org/, '/'),
      },
      "/static": {  // allows the browser to access static resources of the backend directly
        target: (process.env.backend_host || "http://127.0.0.1:55125"),
        changeOrigin: true,
        secure: false,
      },
      "/metrics": {  // allows the browser to access static resources of the backend directly
        target: (process.env.backend_host || "http://127.0.0.1:55125"),
        changeOrigin: true,
        secure: false,
      },
      "/_kolo": {  // allows the browser to access endpoints of the backend directly
        target: (process.env.backend_host || "http://127.0.0.1:55125"),
        changeOrigin: true,
        secure: false,
        //rewrite: (path) => path.replace(/^\/org/, '/'),
      },
    },
  },
  plugins: [vue()],
  assetsInclude: ["**/*.vert", "**/*.frag", "src/textures/*.jpg", "assets/*"],
})
