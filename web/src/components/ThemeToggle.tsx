import { Moon, Sun, Monitor } from "lucide-react"
import { useTheme } from "./useTheme"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex items-center gap-1 bg-[var(--surface-tertiary)] p-1 rounded-lg">
      <button
        onClick={() => setTheme("light")}
        className={`p-2 rounded-md transition-colors ${
          theme === "light" 
            ? "bg-[var(--surface-primary)] shadow-sm text-[var(--accent-primary)]" 
            : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
        }`}
        title="Light Mode"
      >
        <Sun className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={`p-2 rounded-md transition-colors ${
          theme === "dark" 
            ? "bg-[var(--surface-primary)] shadow-sm text-[var(--accent-primary)]" 
            : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
        }`}
        title="Dark Mode"
      >
        <Moon className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("system")}
        className={`p-2 rounded-md transition-colors ${
          theme === "system" 
            ? "bg-[var(--surface-primary)] shadow-sm text-[var(--accent-primary)]" 
            : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
        }`}
        title="System Preference"
      >
        <Monitor className="w-4 h-4" />
      </button>
    </div>
  )
}
