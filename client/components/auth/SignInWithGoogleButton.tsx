"use client"

import { Button } from "@/components/ui/button"
import { supabase } from "@/lib/supabase-client"

export default function SignInWithGoogleButton() {
  async function handleGoogleLogin() {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
  }

  return (
    <Button
      type="button"
      variant="outline"
      className="w-full"
      onClick={handleGoogleLogin}
    >
      Sign in with Google
    </Button>
  )
}
