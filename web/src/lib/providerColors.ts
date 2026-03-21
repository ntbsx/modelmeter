export const PROVIDER_COLORS = [
  { bg: '#dbeafe', text: '#1e40af' },  // blue
  { bg: '#dcfce7', text: '#166534' },  // green
  { bg: '#f3e8ff', text: '#6b21a8' },  // purple
  { bg: '#fef3c7', text: '#92400e' },  // amber
  { bg: '#ffe4e6', text: '#9f1239' },  // rose
  { bg: '#e0f2fe', text: '#075985' },  // sky
  { bg: '#f0fdf4', text: '#14532d' },  // emerald
  { bg: '#fdf4ff', text: '#7e22ce' },  // violet
]

export function providerColorFor(provider: string | null | undefined): { bg: string; text: string } {
  if (!provider) return PROVIDER_COLORS[0]
  let hash = 0
  for (let i = 0; i < provider.length; i++) {
    hash = ((hash << 5) - hash + provider.charCodeAt(i)) | 0
  }
  return PROVIDER_COLORS[Math.abs(hash) % PROVIDER_COLORS.length]
}
