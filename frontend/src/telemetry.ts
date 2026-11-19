import { getWebInstrumentations, initializeFaro } from '@grafana/faro-web-sdk'
import { TracingInstrumentation } from '@grafana/faro-web-tracing'
import { ReplayInstrumentation } from '@grafana/faro-instrumentation-replay'
import { Config } from './config'
import { BrowserTelemetryConfig } from './telemetryConfig'

export class BrowserTelemetry {
  static initialize (): void {
    const settings = Config.browserTelemetrySettings
    if (!BrowserTelemetryConfig.isConfigured(settings)) return

    initializeFaro({
      url: settings.collectorUrl,
      apiKey: settings.publicApiKey,
      app: {
        name: Config.APP_NAME,
        version: Config.APP_VERSION
      },
      instrumentations: [
        ...getWebInstrumentations({ captureConsole: true }),
        new TracingInstrumentation({
          instrumentationOptions: {
            propagateTraceHeaderCorsUrls: [
              BrowserTelemetryConfig.getApiOriginPattern(
                Config.API_BASE_URL,
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
