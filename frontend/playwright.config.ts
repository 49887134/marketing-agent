import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  workers: 1,
  use: { channel: 'chrome', baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure' },
  webServer: [
    {
      command: `${process.platform === 'win32' ? '..\\backend\\.venv\\Scripts\\python.exe' : '../backend/.venv/bin/python'} -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/health', reuseExistingServer: !process.env.CI,
    },
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  ],
})
