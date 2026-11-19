import react from '@vitejs/plugin-react'
import faroUploader from '@grafana/faro-rollup-plugin'
import { defineConfig, loadEnv, type PluginOption } from 'vite'

export default defineConfig(({ mode }) => {
  const environment: Record<string, string> = loadEnv(
    mode,
    process.cwd(),
    'VITE_'
  )
  const plugins: PluginOption[] = [react()]
  const apiKey: string | undefined = environment.VITE_FARO_API_KEY

  if (apiKey) {
    plugins.push(
      faroUploader({
        appName: 'chipark-frontend',
        endpoint: 'https://faro-api-prod-us-east-2.grafana.net/faro/api/v1',
        appId: '2358',
        stackId: '1931743',
        apiKey,
        gzipContents: true
      })
    )
  }

  return {
    plugins,
    build: { sourcemap: 'hidden' }
  }
})
