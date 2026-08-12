import { Metadata } from 'next'
import StorefrontClient from './StorefrontClient'

type Params = { tenant_slug: string }

export async function generateMetadata(props: { params: Promise<Params> | Params }): Promise<Metadata> {
  const params = await props.params
  const decodedSlug = decodeURIComponent(params.tenant_slug)
  const capitalizedSlug = decodedSlug.charAt(0).toUpperCase() + decodedSlug.slice(1)
  
  return {
    title: capitalizedSlug,
    description: `Welcome to ${capitalizedSlug} on MultiVendor`,
  }
}

export default function StorefrontPage(props: { params: Promise<Params> | Params }) {
  return <StorefrontClient params={props.params} />
}
