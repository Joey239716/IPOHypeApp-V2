"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { supabase } from "@/lib/supabase-client"

const LogoutPage = () => {
  const router = useRouter()

  useEffect(() => {
    async function logoutAndRedirect() {
      await supabase.auth.signOut()
      setTimeout(() => router.push("/"), 2000)
    }

    logoutAndRedirect()
  }, [router])

  return <div>You have logged out... redirecting in a sec.</div>
}

export default LogoutPage
