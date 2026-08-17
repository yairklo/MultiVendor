import { redirect } from 'next/navigation'

// The platform has no single-tenant "home" -- the marketplace listing (every
// opted-in vendor's products, in one place) is the natural landing page for
// a visitor who hasn't picked a specific store yet.
export default function Home() {
  redirect('/marketplace')
}
