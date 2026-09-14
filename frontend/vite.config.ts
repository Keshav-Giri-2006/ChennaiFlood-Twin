/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteStaticCopy } from 'vite-plugin-static-copy'

const cesiumSource = 'node_modules/cesium/Build/Cesium'
// Cesium loads Workers/Assets/Widgets at runtime from this public path.
// vite-plugin-static-copy v4 preserves source directories; stripBase drops node_modules/cesium/Build/Cesium.
const cesiumBaseUrl = 'cesium'

export default defineConfig({
  define: {
    CESIUM_BASE_URL: JSON.stringify(`/${cesiumBaseUrl}`),
  },
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        { src: `${cesiumSource}/ThirdParty`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
        { src: `${cesiumSource}/Workers`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
        { src: `${cesiumSource}/Assets`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
        { src: `${cesiumSource}/Widgets`, dest: cesiumBaseUrl, rename: { stripBase: 4 } },
      ],
    }),
  ],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // Local development: forward API calls to the FastAPI backend.
      '/api': { target: process.env.VITE_BACKEND_ORIGIN ?? 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: {
    chunkSizeWarningLimit: 6000,
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
