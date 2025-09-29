import type { NextApiRequest, NextApiResponse } from 'next';
import { createServerClient } from '@supabase/ssr';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const supabase = createServerClient(
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          // Note: `req.headers.cookie` is a string or undefined; you’ll need to parse it
          const cookieHeader = req.headers.cookie ?? '';
          // You can use a cookie parsing library or simple split logic
          return cookieHeader
            .split('; ')
            .filter(Boolean)
            .map(str => {
              const [name, ...rest] = str.split('=');
              return {
                name,
                value: rest.join('=')
              };
            });
        },
        setAll(cookiesToSet) {
          // cookiesToSet is an array of { name, value, options }
          cookiesToSet.forEach(({ name, value, options }) => {
            // Build a Set-Cookie header; options may include path, expires, etc.
            const parts = [`${name}=${value}`];
            if (options.path) parts.push(`Path=${options.path}`);
            if (options.maxAge != null) parts.push(`Max-Age=${options.maxAge}`);
            if (options.expires) parts.push(`Expires=${options.expires.toUTCString()}`);
            if (options.httpOnly) parts.push('HttpOnly');
            if (options.secure) parts.push('Secure');
            if (options.sameSite) parts.push(`SameSite=${options.sameSite}`);
            const prev = res.getHeader('Set-Cookie');
            const prevArr = Array.isArray(prev)
              ? prev
              : prev
              ? [String(prev)]
              : [];
            res.setHeader('Set-Cookie', prevArr.concat(parts.join('; ')));
          });
        }
      }
    }
  );

  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (!user) {
    console.error('[AUTH ERROR]', authError?.message);
    return res.status(401).json({ rows: [], error: 'Unauthorized' });
  }

  try {
    const { data, error } = await supabase.rpc('get_upcoming_table_sorted', {});

    if (error) {
      console.error('[SUPABASE RPC ERROR]', error);
      return res.status(500).json({ rows: [], error: error.message });
    }

    res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate');
    return res.status(200).json({ rows: data ?? [], source: 'supabase' });
  } catch (e: any) {
    console.error('[API ERROR]', e);
    return res.status(500).json({ rows: [], error: e.message ?? 'Unexpected error' });
  }
}
