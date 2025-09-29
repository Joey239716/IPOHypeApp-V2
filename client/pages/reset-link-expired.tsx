"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function ResetLinkExpired() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md shadow-lg border border-gray-200 dark:border-gray-700">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-semibold">
            🔒 Reset Link Expired
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-gray-700 dark:text-gray-300 text-sm text-center">
            This password reset link is no longer valid. It may have already been used or expired.
          </p>

          <div className="flex flex-col gap-3">
            <Button asChild className="w-full">
              <Link href="/reset-password">Request a New Link</Link>
            </Button>

            <Button asChild variant="outline" className="w-full">
              <Link href="/">Go Back Home</Link>
            </Button>
          </div>

          <p className="text-xs text-center text-gray-500 dark:text-gray-400">
            If you're still having trouble, try logging in or contact support.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
