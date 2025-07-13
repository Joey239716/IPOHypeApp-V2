'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { Menu, X, Settings } from 'lucide-react'

const navItems = [
  { label: 'Home', href: '/' },
  { label: 'About', href: '/about' },
  { label: 'Services', href: '/services' },
  { label: 'Contact', href: '/contact' },
]

const topNavItems = [
  {
    label: 'Settings',
    href: '/settings',
    icon: <Settings size={16} className="inline-block mr-1" />,
  },
  { label: 'Log In', href: '/login' },
  { label: 'Sign Up', href: '/signup', highlight: true },
]

export default function Navbar() {
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-50">
      {/* ✅ Top navbar - visible only on md and up */}
      <div className="hidden md:block bg-white dark:bg-gray-900 text-xs border-b-[0.5px] border-gray-200 dark:border-gray-500 pt-2.5 pb-3">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-end space-x-2 text-gray-700 dark:text-gray-300">
          <Link
            href="/settings"
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-md border border-neutral-200 dark:border-gray-500 bg-transparent px-1.5 py-1 font-medium text-neutral-600 transition-all hover:bg-[#eeeeee] dark:hover:bg-neutral-700 select-none cursor-pointer [box-shadow:0px_4px_1px_#d4d4d4] active:translate-y-[2px] active:shadow-none pb-1.5 pt-0.5"
          >
            <Settings size={16} className="mr-0" />
          </Link>
          <Link
            href="/login"
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-md border border-neutral-200 dark:border-gray-500 bg-transparent px-2 py-1 font-medium text-neutral-600 transition-all hover:bg-[#eeeeee] dark:hover:bg-neutral-700 select-none cursor-pointer [box-shadow:0px_4px_1px_#d4d4d4] active:translate-y-[2px] active:shadow-none pb-1.5 pt-0.5"
          >
            Log In
          </Link>
          <Link
            href="/signup"
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-md border border-[#0356a8] dark:border-gray-500 bg-[#0466c8] text-white px-2 py-1 font-medium transition-all hover:bg-[#0356a8] select-none cursor-pointer [box-shadow:0px_4px_1px_#034b8f] active:translate-y-[2px] active:shadow-none pb-1.5 pt-0.5"
          >
            Sign Up
          </Link>
        </div>
      </div>

      {/* ✅ Bottom navbar */}
      <div className="bg-white dark:bg-gray-900 transition-colors duration-300 border-b-[0.5px] border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-[68px]">
            {/* Logo */}
            <Link href="/" className="text-xl font-bold text-[#334155] dark:text-gray-100 select-none cursor-pointer">
              MySite
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex space-x-6">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`text-base font-medium select-none cursor-pointer ${
                    pathname === item.href
                      ? 'text-blue-600 dark:text-blue-400 font-semibold'
                      : 'text-gray-700 dark:text-gray-300 hover:[color:#0466c8] dark:hover:text-blue-400'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>

            {/* Mobile toggle */}
            <div className="md:hidden">
              <button
                onClick={() => setIsOpen(!isOpen)}
                className="text-gray-800 dark:text-gray-100 focus:outline-none"
                aria-label="Toggle menu"
              >
                {isOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
            </div>
          </div>
        </div>

        {/* ✅ Mobile dropdown menu */}
        {isOpen && (
          <div className="md:hidden px-4 pb-4 bg-white dark:bg-gray-900 transition-colors duration-300 space-y-3">
            {/* Normal nav items */}
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`block py-2 px-4 text-base font-medium rounded-md select-none cursor-pointer
                  ${
                    pathname === item.href
                      ? 'text-blue-600 dark:text-blue-400 font-semibold'
                      : 'text-gray-700 dark:text-gray-300 hover:[color:#0466c8] dark:hover:text-blue-400'
                  }
                `}
              >
                {item.label}
              </Link>
            ))}

            <hr className="border-[0.5px] border-gray-300 dark:border-gray-700" />

            {/* ✅ Mobile top navbar buttons with same shadow */}
            {topNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center justify-center space-x-1 py-2 px-4 border rounded-md font-medium transition-colors duration-200 select-none cursor-pointer
                  ${
                    pathname === item.href
                      ? 'text-blue-600 dark:text-blue-400 font-semibold'
                      : 'text-gray-700 dark:text-gray-300 hover:[color:#0466c8] dark:hover:text-blue-400'
                  }
                  ${item.highlight
                    ? 'bg-[#0466c8] border-[#0356a8] text-white hover:bg-[#0356a8]'
                    : 'border-gray-400 dark:border-gray-600 hover:bg-[#eeeeee] dark:hover:bg-neutral-700'}
                  ${
                    item.highlight
                      ? '[box-shadow:0px_4px_1px_#034b8f]'
                      : '[box-shadow:0px_4px_1px_#bdbdbd]'
                  } 
                  active:translate-y-[2px] active:shadow-none
                `}
                style={{ fontSize: '0.75rem' }}
              >
                {item.icon && item.icon}
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
