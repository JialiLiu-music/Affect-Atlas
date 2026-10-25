import { defineConfig } from 'vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  resolve: { tsconfigPaths: true },
  server: { port: 5173, strictPort: true, host: 'localhost' },
  preview: { port: 5173, strictPort: true, host: 'localhost' },
  plugins: [tailwindcss(), tanstackStart(), viteReact()],
})
