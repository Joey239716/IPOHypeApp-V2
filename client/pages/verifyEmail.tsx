// pages/verify-email.tsx
"use client"

import { useEffect } from "react"
import { useRouter } from "next/router"
export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-2xl font-bold mb-4">Check Your Email 📬</h1>
      <p className="text-gray-700 max-w-md">
        We’ve sent a verification link to your email address.
        <br />
        Please verify your email before continuing.
      </p>
    </div>
  )
}
