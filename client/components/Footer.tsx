import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-12">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* About Section */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              IPO Street
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Your trusted source for tracking upcoming IPOs and market insights.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Quick Links
            </h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="/"
                  className="text-sm text-gray-600 dark:text-gray-300 hover:text-green-500 dark:hover:text-green-400 transition"
                >
                  Home
                </a>
              </li>
              <li>
                <a
                  href="/about"
                  className="text-sm text-gray-600 dark:text-gray-300 hover:text-green-500 dark:hover:text-green-400 transition"
                >
                  About
                </a>
              </li>
              <li>
                <a
                  href="/faq"
                  className="text-sm text-gray-600 dark:text-gray-300 hover:text-green-500 dark:hover:text-green-400 transition"
                >
                  FAQ
                </a>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Legal
            </h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="/privacy"
                  className="text-sm text-gray-600 dark:text-gray-300 hover:text-green-500 dark:hover:text-green-400 transition"
                >
                  Privacy Policy
                </a>
              </li>
              <li>
                <a
                  href="/terms"
                  className="text-sm text-gray-600 dark:text-gray-300 hover:text-green-500 dark:hover:text-green-400 transition"
                >
                  Terms of Service
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
          <p className="text-center text-sm text-gray-600 dark:text-gray-300">
            &copy; {new Date().getFullYear()} IPO Street. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
