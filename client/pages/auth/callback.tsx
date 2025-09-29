// pages/auth/callback.tsx
import { useEffect } from "react"
import { useRouter } from "next/router"
import { supabase } from "@/lib/supabase-client"

export default function AuthCallback() {
  const router = useRouter()

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.push("/") // Redirect on success
      } else {
        router.push("/login") // Go back if no session
      }
    })
  }, [router])

  return <p>Signing you in...</p>
}
