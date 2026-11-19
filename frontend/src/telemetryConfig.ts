export interface BrowserTelemetrySettings {
  collectorUrl: string | undefined
  publicApiKey: string | undefined
}

export interface ConfiguredBrowserTelemetrySettings
  extends BrowserTelemetrySettings {
  collectorUrl: string
  publicApiKey: string
}

export class BrowserTelemetryConfig {
  static isConfigured(
    settings: BrowserTelemetrySettings
  ): settings is ConfiguredBrowserTelemetrySettings {
    const hasCollectorUrl: boolean = settings.collectorUrl !== undefined
    const hasPublicApiKey: boolean = settings.publicApiKey !== undefined
    if (!hasCollectorUrl && !hasPublicApiKey) return false
    if (!hasCollectorUrl || !hasPublicApiKey) {
      throw new Error(
        'VITE_FARO_URL and VITE_FARO_API_KEY must both be configured.'
      )
    }
    return true
  }

  static getApiOriginPattern(apiBaseUrl: string, pageOrigin: string): RegExp {
    const apiOrigin: string = new URL(apiBaseUrl, pageOrigin).origin
    const escapedApiOrigin: string = apiOrigin.replace(
      /[.*+?^${}()|[\]\\]/g,
      '\\$&'
    )
    return new RegExp(`^${escapedApiOrigin}(?:/|$)`)
  }
}
