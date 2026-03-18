import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTokens(value: number): string {
  if (value === undefined || value === null) return "0"
  
  const absValue = Math.abs(value)
  let short: string
  
  if (absValue >= 1_000_000_000) {
    short = (value / 1_000_000_000).toFixed(1) + "B"
  } else if (absValue >= 1_000_000) {
    short = (value / 1_000_000).toFixed(1) + "M"
  } else if (absValue >= 1_000) {
    short = (value / 1_000).toFixed(1) + "K"
  } else {
    return value.toLocaleString()
  }
  
  return short
}

export function formatUsd(value: number): string {
  if (value === undefined || value === null) return "$0.00"
  
  const absValue = Math.abs(value)
  if (absValue >= 1_000_000_000) {
    return "$" + (value / 1_000_000_000).toFixed(1) + "B"
  } else if (absValue >= 1_000_000) {
    return "$" + (value / 1_000_000).toFixed(1) + "M"
  } else if (absValue >= 1_000) {
    return "$" + (value / 1_000).toFixed(1) + "K"
  } else if (absValue >= 1) {
    return "$" + value.toFixed(2)
  }
  return "$" + value.toFixed(4)
}
