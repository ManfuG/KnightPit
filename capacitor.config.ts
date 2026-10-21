import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'io.github.manfug.knightpit',
  appName: 'KnightPit',
  webDir: 'dist',
  server: { hostname: 'localhost', androidScheme: 'https' },
  android: { backgroundColor: '#101e2b', minWebViewVersion: 119 },
  plugins: { SystemBars: { insetsHandling: 'disable', style: 'DARK' } },
}

export default config
