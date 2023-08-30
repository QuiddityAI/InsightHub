import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    proxy: {
      "/data_backend": {
        target: "http://127.0.0.1:55123",
        changeOrigin: true,
        secure: false,
      },
      "/organization_backend": {
        target: "http://127.0.0.1:55125",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/organization_backend/, '/data_map/'),
      },
    },
  },
  plugins: [vue()],
  assetsInclude: ["**/*.vert", "**/*.frag"],
})
