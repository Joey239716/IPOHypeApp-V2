'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Menu, X, Settings } from 'lucide-react'

const navItems = [
  { label: 'Home', href: '/' },
  { label: 'About', href: '/about' },
  { label: 'Services', href: '/services' },
  { label: 'Contact', href: '/contact' },
]

const topNavItems = [
  { label: 'Log In', href: '/login' },
  { label: 'Sign Up', href: '/signup', highlight: true },
]

export default function Navbar() {
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('theme')
    const isDark =
      stored === 'dark' ||
      (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)
    setDarkMode(isDark)
    document.documentElement.classList.toggle('dark', isDark)
  }, [])

  const toggleDarkMode = () => {
    const next = !darkMode
    setDarkMode(next)
    document.documentElement.classList.toggle('dark', next)
    localStorage.setItem('theme', next ? 'dark' : 'light')
  }

  return (
    <nav className="sticky top-0 z-50 select-none">
      {/* Top navbar (md+) */}
      <div
        className="
          hidden md:block
          bg-white dark:bg-gray-900
          transition-colors
          border-b-[0.5px] border-gray-200 dark:border-gray-500
          pt-2.5 pb-3 text-xs
        "
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-end space-x-2 text-gray-700 dark:text-gray-300">
          {/* Settings dropdown button */}
          <div className="relative">
            <button
              onClick={() => setSettingsOpen(!settingsOpen)}
              className="
                group relative inline-flex items-center justify-center overflow-hidden rounded-md
                border border-neutral-200 dark:border-gray-500 bg-transparent
                px-1.5 py-1 font-medium text-neutral-600 dark:text-neutral-300
                transition-all hover:bg-[#eeeeee] dark:hover:bg-neutral-700
                select-none focus:outline-none
                [box-shadow:0px_4px_1px_#d4d4d4] dark:[box-shadow:0px_4px_1px_#838383]
                active:translate-y-[2px] active:shadow-none
                pb-1.5 pt-0.5
              "
            >
              <Settings size={16} />
            </button>

            {settingsOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-50">
                <Link
                  href="/settings/profile"
                  className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 select-none focus:outline-none"
                >
                  Profile
                </Link>
                <Link
                  href="/settings/account"
                  className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 select-none focus:outline-none"
                >
                  Account
                </Link>
                <div className="flex items-center justify-between px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 select-none">
                  <span className="text-sm text-gray-700 dark:text-gray-200">
                    Dark Mode
                  </span>
                  <label className="relative inline-flex items-center cursor-pointer select-none">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={darkMode}
                      onChange={toggleDarkMode}
                    />
                    <div className="w-10 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-blue-300 dark:bg-gray-700 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                    <div className="absolute left-0.5 bg-white w-4 h-4 rounded-full transition-transform peer-checked:translate-x-5" />
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Log In button */}
          <Link
            href="/login"
            className="
              group relative inline-flex items-center justify-center overflow-hidden rounded-md
              border border-neutral-200 dark:border-gray-500 bg-transparent
              px-2 py-1 font-medium text-neutral-600 dark:text-neutral-300
              transition-all hover:bg-[#eeeeee] dark:hover:bg-neutral-700
              select-none caret-transparent focus:outline-none cursor-pointer
              [box-shadow:0px_4px_1px_#d4d4d4] dark:[box-shadow:0px_4px_1px_#838383]
              active:translate-y-[2px] active:shadow-none
              pb-1.5 pt-0.5
            "
          >
            Log In
          </Link>

          {/* Sign Up button */}
          <Link
            href="/signup"
            className="
              group relative inline-flex items-center justify-center overflow-hidden rounded-md
              border border-[#0356a8] dark:border-gray-500 bg-[#0466c8] text-white
              px-2 py-1 font-medium transition-all hover:bg-[#0356a8]
              select-none caret-transparent focus:outline-none cursor-pointer
              [box-shadow:0px_4px_1px_#034b8f] active:translate-y-[2px] active:shadow-none
              pb-1.5 pt-0.5
            "
          >
            Sign Up
          </Link>
        </div>
      </div>

      {/* Bottom navbar (re-added border) */}
      <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link
              href="/"
              className="text-xl font-bold text-gray-800 dark:text-gray-100 select-none caret-transparent focus:outline-none"
            >
              MySite
            </Link>

            <div className="hidden md:flex space-x-6">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`text-base font-medium select-none caret-transparent focus:outline-none ${
                    pathname === item.href
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>

            {/* Mobile menu toggle */}
            <div className="md:hidden">
              <button
                onClick={() => setIsOpen(!isOpen)}
                className="p-2 rounded-md focus:outline-none focus:ring select-none"
                aria-label="Toggle menu"
              >
                {isOpen ? (
                  <X size={24} className="text-gray-800 dark:text-gray-100" />
                ) : (
                  <Menu size={24} className="text-gray-800 dark:text-gray-100" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile dropdown */}
        {isOpen && (
          <div className="md:hidden px-4 pb-4 bg-white dark:bg-gray-900 space-y-3">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`block px-4 py-2 rounded-md select-none caret-transparent focus:outline-none ${
                  pathname === item.href
                    ? 'bg-blue-50 dark:bg-gray-800 text-blue-600'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                {item.label}
              </Link>
            ))}

            <hr className="border-t border-gray-300 dark:border-gray-700" />

            <div className="flex items-center justify-between px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 select-none">
              <span className="text-sm text-gray-700 dark:text-gray-200">
                Dark Mode
              </span>
              <label className="relative inline-flex items-center cursor-pointer select-none">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={darkMode}
                  onChange={toggleDarkMode}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-blue-300 dark:bg-gray-700 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                <div className="absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            {topNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`block px-4 py-2 rounded-md select-none caret-transparent focus:outline-none ${
                  item.highlight
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
