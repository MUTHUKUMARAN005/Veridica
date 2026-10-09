export type ServiceStatus = 'connected' | 'unavailable' | 'unknown'
export type HealthSnapshot = Record<'api' | 'postgres' | 'redis', ServiceStatus>

export async function getHealth(signal: AbortSignal): Promise<HealthSnapshot> {
  try {
    const response = await fetch('/api/v1/health/ready', {
      signal: AbortSignal.any([signal, AbortSignal.timeout(8000)]),
      cache: 'no-store',
    })
    if (response.status !== 200 && response.status !== 503) throw new Error('API unavailable')
    const data = await response.json()
    const statuses = ['connected', 'unavailable']
    if (!statuses.includes(data?.services?.postgres) || !statuses.includes(data?.services?.redis)) {
      throw new Error('Invalid health response')
    }
    return { api: 'connected', postgres: data.services.postgres, redis: data.services.redis }
  } catch {
    return { api: 'unavailable', postgres: 'unknown', redis: 'unknown' }
  }
}