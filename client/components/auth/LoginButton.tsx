"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/router"
import Link from "next/link"
import { supabase } from "@/lib/supabase-client"
import { Button } from "@/components/ui/button"

const AuthButtons = () => {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const fetchUser = async () => {
      const { data } = await supabase.auth.getUser()
      setUser(data.user)
    }
    fetchUser()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    setUser(null)
    router.push("/login")
  }

  if (user) {
    return (
      <div className="flex gap-2 items-center">
        <span className="text-sm">Hi, {user.user_metadata?.full_name || user.email}</span>
        <Button variant="outline" onClick={handleLogout}>
          Log out
        </Button>
      </div>
    )
  }

  return (
    <div className="flex gap-2">
      <Link href="/login">
        <Button variant="outline">Login</Button>
      </Link>
      <Link href="/signup">
        <Button>Sign up</Button>
      </Link>
    </div>
  )
}

export default AuthButtons
