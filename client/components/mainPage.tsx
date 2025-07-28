'use client'

import React, { useState /*, useEffect */ } from 'react'
import Navbar from './navbar'

interface IPO {
  cik: string
  companyName: string
  form_type: string
  date_filed: string
}

// Mock data for styling/testing purposes
const MOCK_DATA: Record<string, Omit<IPO, 'cik'>> = {
  "1083220": { companyName: "XCel Brands, Inc.", form_type: "S-1", date_filed: "20250702" },
  "1859007": { companyName: "ZyVersa Therapeutics, Inc.", form_type: "S-1", date_filed: "20250702" },
  "1948864": { companyName: "HEALTHY CHOICE WELLNESS CORP.", form_type: "S-1", date_filed: "20250702" },
  "1083522": { companyName: "JONES SODA CO", form_type: "S-1", date_filed: "20250703" },
  "1500412": { companyName: "Ambiq Micro, Inc.", form_type: "S-1", date_filed: "20250703" },
  "1580149": { companyName: "BIOVIE INC.", form_type: "S-1", date_filed: "20250703" },
  "1758009": { companyName: "Quantum Computing Inc.", form_type: "S-1", date_filed: "20250703" },
  "1855485": { companyName: "Calidi Biotherapeutics, Inc.", form_type: "S-1", date_filed: "20250703" },
  "2047177": { companyName: "Chenghe Acquisition III Co.", form_type: "S-1", date_filed: "20250703" },
  "2075280": { companyName: "Global Thrive Fulfill Group Inc", form_type: "S-1", date_filed: "20250703" },
}

export default function MainPage() {
  const [ipos /*, setIpos */] = useState<IPO[]>(
    Object.entries(MOCK_DATA).map(([cik, info]) => ({ cik, ...info }))
  )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 select-none caret-transparent">
      <Navbar />
      <main className="max-w-7xl mx-auto p-4">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          Upcoming IPOs
        </h1>

        <div className="overflow-x-auto">
          <table className="w-full table-auto border-collapse text-left select-none caret-transparent">
            <thead className="border-b border-gray-300 dark:border-gray-700">
              <tr>
                <th className="px-6 py-3 text-sm font-semibold text-gray-500 dark:text-gray-400">Name</th>
                <th className="px-6 py-3 text-sm font-semibold text-gray-500 dark:text-gray-400">CIK</th>
                <th className="px-6 py-3 text-sm font-semibold text-gray-500 dark:text-gray-400">Date Filed</th>
                <th className="px-6 py-3 text-sm font-semibold text-gray-500 dark:text-gray-400">Form Type</th>
              </tr>
            </thead>
            <tbody>
              {ipos.map((ipo) => (
                <tr
                  key={ipo.cik}
                  className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 select-none caret-transparent"
                >
                  <td className="px-6 py-4 text-sm text-gray-800 dark:text-gray-200">{ipo.companyName}</td>
                  <td className="px-6 py-4 text-sm text-gray-800 dark:text-gray-200">{ipo.cik}</td>
                  <td className="px-6 py-4 text-sm text-gray-800 dark:text-gray-200">{ipo.date_filed}</td>
                  <td className="px-6 py-4 text-sm text-gray-800 dark:text-gray-200">{ipo.form_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
