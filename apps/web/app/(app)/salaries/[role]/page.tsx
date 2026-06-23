import Link from "next/link"
import { notFound } from "next/navigation"

export const revalidate = 86400

interface Props {
  params: { role: string }
}

function slugToLabel(slug: string): string {
  return slug.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
}

export default async function SalariesRoleIndexPage({ params }: Props) {
  const role = slugToLabel(params.role)
  
  let cities = [];
  try {
    const apiUrl = [process.env.INTERNAL_API_URL, process.env.NEXT_PUBLIC_API_URL, "http://127.0.0.1:8000"].find(u => u && u !== "undefined");
    const res = await fetch(
      `${apiUrl}/v1/salaries/${params.role}/cities`,
      { next: { revalidate: 86400 } }
    )
    if (res.ok) {
      const data = await res.json();
      cities = data.cities ?? [];
    } else if (res.status === 404) {
      notFound();
    }
  } catch (e) {
    console.warn(`Backend offline during build, skipping cities fetch for ${params.role}`);
  }
  
  if (cities.length === 0) {
      notFound()
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900">
        {role} Salary Guide by City — {new Date().getFullYear()}
      </h1>
      <p className="mt-2 text-gray-500">
        Live salary data across India based on active job listings.
      </p>
      
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cities.map((c: any) => (
          <Link
            key={c.city_slug}
            href={`/salaries/${params.role}/${c.city_slug}`}
            className="rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-200 hover:shadow-sm transition-all block"
          >
            <p className="font-medium text-gray-900">
              {c.city_slug.charAt(0).toUpperCase() + c.city_slug.slice(1)}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {c.count.toLocaleString("en-IN")} listings
            </p>
            {c.median != null && (
              <p className="mt-2 text-sm font-semibold text-blue-600">
                ₹{(c.median / 100000).toFixed(1)}L median
              </p>
            )}
          </Link>
        ))}
      </div>
    </main>
  )
}
