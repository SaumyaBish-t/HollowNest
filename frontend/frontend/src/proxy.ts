import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

// Routes that anyone (signed in or out) can hit. Everything else requires a
// signed-in user — protected by middleware before the page even renders.
const isPublicRoute = createRouteMatcher([
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/health(.*)',
])

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    // Skip Next.js internals + static files unless found in search params.
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API + tRPC routes.
    '/(api|trpc)(.*)',
  ],
}
