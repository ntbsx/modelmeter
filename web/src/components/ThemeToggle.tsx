import { Moon, Sun, Monitor } from "lucide-react"
import { useTheme } from "./ThemeProvider"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
      <button
        onClick={() => setTheme("light")}
        className={`p-2 rounded-md transition-colors ${
          theme === "light" 
            ? "bg-white dark:bg-gray-700 shadow-sm text-blue-600 dark:text-blue-400" 
            : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        }`}
        title="Light Mode"
      >
        <Sun className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={`p-2 rounded-md transition-colors ${
          theme === "dark" 
            ? "bg-white dark:bg-gray-700 shadow-sm text-blue-600 dark:text-blue-400" 
            : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        }`}
        title="Dark Mode"
      >
        <Moon className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("system")}
        className={`p-2 rounded-md transition-colors ${
          theme === "system" 
            ? "bg-white dark:bg-gray-700 shadow-sm text-blue-600 dark:text-blue-400" 
            : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        }`}
        title="System Preference"
      >
        <Monitor className="w-4 h-4" />
      </button>
    </div>
  )
}
