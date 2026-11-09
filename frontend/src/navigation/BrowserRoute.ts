export interface RouteState {
  pathname: string
  search: string
}

export class BrowserRoute {
  static current(): RouteState {
    return {
      pathname: window.location.pathname,
      search: window.location.search
    }
  }
}

export class AuthTokenStore {
  private static readonly STORAGE_KEY: string = 'chipark_access_token'

  static getInitialToken(): string | null {
    const url: URL = new URL(window.location.href)
    if (url.pathname === '/auth/callback') {
      const callbackValues: URLSearchParams = new URLSearchParams(url.hash.slice(1))
      const callbackToken: string | null = callbackValues.get('access_token')
      if (callbackToken !== null) {
        window.localStorage.setItem(AuthTokenStore.STORAGE_KEY, callbackToken)
        window.history.replaceState(null, '', `${url.pathname}${url.search}`)
        return callbackToken
      }
    }
    return window.localStorage.getItem(AuthTokenStore.STORAGE_KEY)
  }

  static save(token: string): void {
    window.localStorage.setItem(AuthTokenStore.STORAGE_KEY, token)
  }

  static clear(): void {
    window.localStorage.removeItem(AuthTokenStore.STORAGE_KEY)
  }
}

export class RouteParameters {
  static getNextPath(search: string): string {
    const requestedPath: string | null = new URLSearchParams(search).get('next')
    if (
      requestedPath === null ||
      !requestedPath.startsWith('/') ||
      requestedPath.startsWith('//')
    ) {
      return '/parks'
    }
    return requestedPath
  }

  static getIdFromPath(pathname: string, expression: RegExp): number | null {
    const match: RegExpMatchArray | null = pathname.match(expression)
    if (match === null) return null
    const id: number = Number(match[1])
    return Number.isSafeInteger(id) && id > 0 ? id : null
  }
}
