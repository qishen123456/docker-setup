import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const viteCacheDir = process.env.SMARTASK_VITE_CACHE_DIR || resolve(tmpdir(), 'smartask-vite-cache')

export default defineConfig({
  plugins: [vue()],
  cacheDir: viteCacheDir,
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 代理：前端 /api 请求自动转发到后端 5000 端口（避免跨域）
    proxy: {
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true
      }
    }
  }
})
