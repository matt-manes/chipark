import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import test from 'node:test'
import {
  ChiparkApiClient
} from '../src/api/ChiparkApiClient.ts'
import type { TicketNotification } from '../src/api/types.ts'

interface CapturedRequest {
  method: string
  path: string
  authorization: string | undefined
  lastEventId: string | undefined
  body: string
}

class ApiTestServer {
  private readonly server: Server
  readonly requests: CapturedRequest[] = []
  readonly blockedResponse: Promise<void>
  private releaseBlockedResponse: (() => void) | null = null
  private delayParksResponse: boolean = false

  constructor() {
    this.blockedResponse = new Promise(resolve => {
      this.releaseBlockedResponse = resolve
    })
    this.server = createServer((request, response) => {
      void this.handle(request, response)
    })
  }

  async start(): Promise<string> {
    await new Promise<void>((resolve, reject) => {
      this.server.once('error', reject)
      this.server.listen(0, '127.0.0.1', () => resolve())
    })
    const address: AddressInfo | string | null = this.server.address()
    if (address === null || typeof address === 'string') {
      throw new Error('The API test server did not bind to a TCP address.')
    }
    return `http://127.0.0.1:${address.port}`
  }

  async close(): Promise<void> {
    this.releaseBlockedResponse?.()
    await new Promise<void>((resolve, reject) => {
      this.server.close(error => {
        if (error !== undefined) reject(error)
        else resolve()
      })
    })
  }

  holdParkResponse(): void {
    this.delayParksResponse = true
  }

  private async handle(
    request: IncomingMessage,
    response: ServerResponse
  ): Promise<void> {
    const chunks: Buffer[] = []
    for await (const chunk of request) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))
    }

    const body: string = Buffer.concat(chunks).toString('utf8')
    const path: string = request.url ?? '/'
    this.requests.push({
      method: request.method ?? 'GET',
      path,
      authorization: request.headers.authorization,
      lastEventId:
        typeof request.headers['last-event-id'] === 'string'
          ? request.headers['last-event-id']
          : undefined,
      body
    })

    if (path === '/notifications/stream') {
      response.writeHead(200, { 'Content-Type': 'text/event-stream' })
      response.end(
        'id: 42\n' +
          'event: ticket_updated\n' +
          'data: {"notification_id":42,"event_type":"ticket_updated",' +
          '"ticket_id":9,"park_name":"Sample Park","issue":"Updated",' +
          '"created_at":"2026-11-09T12:00:00","read_at":null}\n\n'
      )
      return
    }

    if (path === '/parks' && this.delayParksResponse) {
      await this.blockedResponse
    }

    if (path === '/auth/logout') {
      response.writeHead(204)
      response.end()
      return
    }

    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify(this.getResponseBody(path)))
  }

  private getResponseBody(path: string): unknown {
    if (path === '/auth/login' || path === '/auth/register') {
      return {
        access_token: 'issued-token',
        token_type: 'Bearer',
        expires_at: '2026-11-10T12:00:00',
        user: {
          user_id: 1,
          email: 'member@example.com',
          role: 'user',
          password_login_enabled: true,
          google_login_enabled: false
        }
      }
    }
    if (path.startsWith('/auth/me')) {
      return {
        user_id: 1,
        email: 'member@example.com',
        role: 'user',
        password_login_enabled: true,
        google_login_enabled: false
      }
    }
    if (path.endsWith('/conditions')) return null
    return []
  }
}

async function withApiServer(
  callback: (api: ChiparkApiClient, server: ApiTestServer) => Promise<void>
): Promise<void> {
  const server: ApiTestServer = new ApiTestServer()
  const baseUrl: string = await server.start()
  try {
    await callback(new ChiparkApiClient(baseUrl), server)
  } finally {
    await server.close()
  }
}

test('auth and profile methods use their expected endpoints and bearer token', async () => {
  await withApiServer(async (api, server) => {
    const session = await api.login('member@example.com', 'password')
    assert.equal(session.access_token, 'issued-token')

    api.setAccessToken(session.access_token)
    await api.getCurrentUser()
    await api.updateProfile({ email: 'updated@example.com' })
    await api.logout()

    assert.deepEqual(
      server.requests.map(request => [request.method, request.path]),
      [
        ['POST', '/auth/login'],
        ['GET', '/auth/me'],
        ['PATCH', '/auth/me'],
        ['POST', '/auth/logout']
      ]
    )
    assert.equal(server.requests[0].body, JSON.stringify({
      email: 'member@example.com',
      password: 'password'
    }))
    assert.equal(server.requests[1].authorization, 'Bearer issued-token')
    assert.equal(server.requests[2].authorization, 'Bearer issued-token')
    assert.equal(server.requests[3].authorization, 'Bearer issued-token')
  })
})

test('park and ticket methods use their expected endpoints and payloads', async () => {
  await withApiServer(async (api, server) => {
    await api.register('member@example.com', 'password')
    await api.getParks()
    await api.getPark(3)
    await api.getConditions(3)
    await api.getOpenTicketsForPark(3)
    await api.getTickets()
    await api.getTicket(9)
    await api.getMyTickets()
    await api.submitTicket({
      park_name: 'Sample Park',
      issue: 'Broken bench'
    })
    await api.updateTicket(9, { issue: 'Updated issue', status: 2 })
    await api.closeTicket(9)
    await api.reopenTicket(9)

    assert.deepEqual(
      server.requests.map(request => [request.method, request.path]),
      [
        ['POST', '/auth/register'],
        ['GET', '/parks'],
        ['GET', '/parks/3'],
        ['GET', '/parks/3/conditions'],
        ['GET', '/tickets/parks/3/open'],
        ['GET', '/tickets'],
        ['GET', '/tickets/9'],
        ['GET', '/tickets/mine'],
        ['POST', '/tickets'],
        ['PATCH', '/tickets/9'],
        ['PATCH', '/tickets/9/close'],
        ['PATCH', '/tickets/9/reopen']
      ]
    )
    assert.equal(
      server.requests[8].body,
      JSON.stringify({ park_name: 'Sample Park', issue: 'Broken bench' })
    )
    assert.equal(
      server.requests[9].body,
      JSON.stringify({ issue: 'Updated issue', status: 2 })
    )
  })
})

test('read methods pass an abort signal to Axios', async () => {
  await withApiServer(async (api, server) => {
    server.holdParkResponse()
    const controller: AbortController = new AbortController()
    const request: Promise<unknown> = api.getParks(controller.signal)
    while (server.requests.length === 0) {
      await new Promise(resolve => setTimeout(resolve, 1))
    }
    controller.abort()

    await assert.rejects(request, { code: 'ERR_CANCELED' })
  })
})

test('notification stream sends auth and cursor headers and parses event data', async () => {
  await withApiServer(async (api, server) => {
    api.setAccessToken('stream-token')
    const notifications: TicketNotification[] = []
    const controller: AbortController = new AbortController()

    await api.streamNotifications(controller.signal, 41, notification => {
      notifications.push(notification)
    })

    assert.equal(server.requests[0].path, '/notifications/stream')
    assert.equal(server.requests[0].authorization, 'Bearer stream-token')
    assert.equal(server.requests[0].lastEventId, '41')
    assert.equal(notifications.length, 1)
    assert.equal(notifications[0].notification_id, 42)
    assert.equal(notifications[0].ticket_id, 9)
    assert.equal(notifications[0].event_type, 'ticket_updated')
  })
})

test('notification stream reports a missing access token', async () => {
  const api: ChiparkApiClient = new ChiparkApiClient('http://127.0.0.1')

  await assert.rejects(
    api.streamNotifications(new AbortController().signal, null, () => undefined),
    /Sign in is required/
  )
})
