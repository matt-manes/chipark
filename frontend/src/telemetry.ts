import { getWebInstrumentations, initializeFaro } from '@grafana/faro-web-sdk'
import { TracingInstrumentation } from '@grafana/faro-web-tracing'
import { ReplayInstrumentation } from '@grafana/faro-instrumentation-replay'
import { API_BASE_URL } from './config'
import {
  BrowserTelemetryConfig,
  type BrowserTelemetrySettings
} from './telemetryConfig'

export class BrowserTelemetry {
  static initialize (): void {
    const settings: BrowserTelemetrySettings = {
      collectorUrl: import.meta.env?.VITE_FARO_URL,
      publicApiKey: import.meta.env?.VITE_FARO_API_KEY
    }
    if (!BrowserTelemetryConfig.isConfigured(settings)) return

    initializeFaro({
      url: settings.collectorUrl,
      apiKey: settings.publicApiKey,
      app: {
        name: 'chipark-frontend',
        version: import.meta.env.VITE_APP_VERSION ?? 'development'
      },
      instrumentations: [
        ...getWebInstrumentations({ captureConsole: true }),
        new TracingInstrumentation({
          instrumentationOptions: {
            propagateTraceHeaderCorsUrls: [
              BrowserTelemetryConfig.getApiOriginPattern(
                API_BASE_URL,
                window.location.origin
              )
            ]
          }
        }),
        new ReplayInstrumentation({
          maskAllInputs: false,
          maskInputOptions: {
            password: true,
            email: true
          },
          maskTextSelector: '.grafana-mask',
          blockSelector: '.grafana-block, input[type="hidden"]',
          ignoreSelector: '.grafana-ignore'
        })
      ]
    })
  }
}
