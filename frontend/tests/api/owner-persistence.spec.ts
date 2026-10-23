import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'

const password = 'phase-eight-browser-password'

test('browser owner flow persists an idea through the authenticated API and a new login', async ({ page }) => {
  const email = `browser-e2e-${randomUUID()}@example.invalid`
  await page.goto('/#/auth')
  await page.getByRole('tab', { name: 'Create account', exact: true }).click()
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page.getByText(`API · ${email}`, { exact: true })).toBeVisible()

  await page.getByRole('link', { name: 'New idea', exact: true }).click()
  await page.getByLabel(/Idea title/).fill('Browser persisted idea')
  await page.getByLabel('Target users').fill('Local students')
  await page.getByLabel('Problem statement').fill(
    'Students need a reliable way to organize placement preparation.',
  )
  await page.getByLabel('Proposed solution').fill(
    'A guided workspace that keeps preparation steps together.',
  )
  await page.getByLabel('Core features').fill('Preparation roadmap\nOpportunity list')
  await page.getByLabel('Constraints and considerations').fill('No external integrations.')
  const createIdeaResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/ideas') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Save idea', exact: true }).click()
  const response = await createIdeaResponse
  expect(response.status(), await response.text()).toBe(201)
  await expect(page.getByRole('heading', { name: 'Browser persisted idea', exact: true })).toBeVisible()
  await expect(page.getByText('Authenticated API', { exact: true })).toBeVisible()

  await page.reload()
  await page.goto('/#/auth')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByText(`API · ${email}`, { exact: true })).toBeVisible()
  await page.goto('/#/ideas')
  await expect(page.getByRole('heading', { name: 'Browser persisted idea', exact: true })).toBeVisible()
  await expect(page.getByText('1 idea', { exact: true })).toBeVisible()
})
