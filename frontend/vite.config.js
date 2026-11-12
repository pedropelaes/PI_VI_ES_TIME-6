// Testes de data dependem do fuso; fixa antes de qualquer uso de Date.
process.env.TZ = 'America/Sao_Paulo'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
