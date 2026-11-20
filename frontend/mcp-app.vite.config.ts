import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: 'dist/mcp-app',
    emptyOutDir: false,
    rollupOptions: {
      input: resolve(process.cwd(), 'mcp-app.html')
    }
  }
})
