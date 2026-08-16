# Next.js Server & Client Components Rule

When working on the `frontend` application in this project (which uses Next.js App Router):

1. **Server Components by Default:** Assume all components are React Server Components unless specified otherwise.
2. **Client Components:** If a component uses any React hooks (such as `useState`, `useEffect`, `useRouter`, `useContext`, `useRef`, etc.) or DOM event listeners (like `onClick`, `onChange`), it MUST be marked as a client component.
3. **Directive:** You MUST add `"use client"` at the very top of the file for all client components. Failure to do so will result in Next.js runtime errors.
4. **Separation of Concerns:** Keep client components as small and leaf-node as possible. Pass data from server components down to client components via props.
