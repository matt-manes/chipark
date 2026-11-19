import type { BrowserTelemetrySettings } from './telemetryConfig'

const DEFAULT_API_BASE_URL: string = 'http://127.0.0.1:8000'
const DEFAULT_APP_NAME: string = 'chipark-frontend'
const DEFAULT_APP_VERSION: string = 'development'

export class Config {
  static readonly API_BASE_URL: string =
    Config.getOptionalValue(import.meta.env?.VITE_API_BASE_URL) ??
    DEFAULT_API_BASE_URL
  static readonly FARO_URL: string | undefined = Config.getOptionalValue(
    import.meta.env?.VITE_FARO_URL
  )
  static readonly FARO_API_KEY: string | undefined = Config.getOptionalValue(
    import.meta.env?.VITE_FARO_API_KEY
  )
  static readonly APP_NAME: string =
    Config.getOptionalValue(import.meta.env?.VITE_APP_NAME) ?? DEFAULT_APP_NAME
  static readonly APP_VERSION: string =
    Config.getOptionalValue(import.meta.env?.VITE_APP_VERSION) ??
    DEFAULT_APP_VERSION

  static get browserTelemetrySettings(): BrowserTelemetrySettings {
    return {
      collectorUrl: Config.FARO_URL,
      publicApiKey: Config.FARO_API_KEY
    }
  }

  private static getOptionalValue(value: string | undefined): string | undefined {
    const trimmedValue: string | undefined = value?.trim()
    return trimmedValue || undefined
  }
}
