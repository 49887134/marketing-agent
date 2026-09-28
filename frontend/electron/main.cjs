const { app, BrowserWindow, protocol, net } = require('electron')
const path = require('node:path')
const { pathToFileURL } = require('node:url')

const isDev = process.argv.includes('--dev')
const devUrl = 'http://127.0.0.1:5173'
protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
])

function createWindow() {
  const window = new BrowserWindow({
    width: 1440, height: 960, minWidth: 800, minHeight: 600,
    title: '百度营销智能运营 Agent', backgroundColor: '#f4f6fa',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  })
  window.setMenuBarVisibility(false)
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event, url) => {
    const target = new URL(url)
    const allowed = isDev ? target.origin === devUrl : target.protocol === 'app:' && target.host === 'dashboard'
    if (!allowed) event.preventDefault()
  })
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false))
  if (isDev) window.loadURL(devUrl)
  else window.loadURL('app://dashboard/index.html')
}

app.whenReady().then(() => {
  // 只提供 dist 内的静态文件，不向渲染页面暴露 Node、IPC 或任意文件访问能力。
  const root = path.resolve(__dirname, '../dist')
  protocol.handle('app', (request) => {
    const url = new URL(request.url)
    if (url.host !== 'dashboard' || request.method !== 'GET') return new Response('Forbidden', { status: 403 })
    let pathname
    try { pathname = decodeURIComponent(url.pathname) } catch { return new Response('Bad Request', { status: 400 }) }
    const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname))
    const relative = path.relative(root, file)
    if (relative.startsWith('..') || path.isAbsolute(relative)) return new Response('Forbidden', { status: 403 })
    return net.fetch(pathToFileURL(file).toString())
  })
  createWindow()
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
})
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
