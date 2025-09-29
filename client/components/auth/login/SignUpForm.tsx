"use client"

import { useRouter } from "next/router"
import { useState } from "react"
import Link from "next/link"
import { supabase } from "@/lib/supabase-client"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function SignUpForm() {
  const router = useRouter()
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

async function handleSignup(e: React.FormEvent<HTMLFormElement>) {
  e.preventDefault()
  setLoading(true)
  setError("")

  const formData = new FormData(e.currentTarget)
  const email = formData.get("email") as string
  const password = formData.get("password") as string
  const firstName = formData.get("first-name") as string
  const lastName = formData.get("last-name") as string

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        first_name: firstName,
        last_name: lastName,
      },
    },
  })

  if (error) {
    const msg = error.message.toLowerCase()

    if (msg.includes("user already registered") || msg.includes("already exists")) {
      setError("ACCOUNT_EXISTS")
    } else {
      setError(error.message)
    }
  } else {
    router.push("/verifyEmail")
  }

  setLoading(false)
}

  async function handleGoogleSignup() {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
  }

  return (
    <Card className="mx-auto max-w-sm">
      <CardHeader>
        <CardTitle className="text-xl">Sign Up</CardTitle>
        <CardDescription>
          Enter your information to create an account.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSignup} className="grid gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="first-name">First name</Label>
              <Input
                name="first-name"
                id="first-name"
                placeholder="Max"
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="last-name">Last name</Label>
              <Input
                name="last-name"
                id="last-name"
                placeholder="Robinson"
                required
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              name="email"
              id="email"
              type="email"
              placeholder="m@example.com"
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input name="password" id="password" type="password" required />
          </div>

          {error && (
  <p className="text-sm text-red-500">
    {error === "ACCOUNT_EXISTS" ? (
      <>
        This account already exists and has been verified.{" "}
        <Link href="/login" className="underline">
          Log in instead.
        </Link>
      </>
    ) : (
      error
    )}
  </p>
)}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Creating account..." : "Create an account"}
          </Button>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={handleGoogleSignup}
          >
            Sign up with Google
          </Button>
        </form>

        <div className="mt-4 text-center text-sm">
          Already have an account?{" "}
          <Link href="/login" className="underline">
            Sign in
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
