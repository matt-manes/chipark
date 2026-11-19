import react from '@vitejs/plugin-react'
import faroUploader from '@grafana/faro-rollup-plugin'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    faroUploader({
      appName: 'chipark-frontend',
      endpoint: 'https://faro-api-prod-us-east-2.grafana.net/faro/api/v1',
      appId: '2358',
      stackId: '1931743',
      // Assuming the existence of environment variable 'FARO_API_KEY'
      apiKey: process.env.VITE_FARO_API_KEY,
      gzipContents: true
    })
  ],
  build: { sourcemap: 'hidden' }
})
