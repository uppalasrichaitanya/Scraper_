import Link from "next/link"

export const revalidate = 86400

export default async function SalariesIndexPage() {
  let data = { combinations: [] };
  try {
    const apiUrl = [process.env.INTERNAL_API_URL, process.env.NEXT_PUBLIC_API_URL, "http://127.0.0.1:8000"].find(u => u && u !== "undefined");
    const res = await fetch(
      `${apiUrl}/v1/salaries/top-combinations`,
      { next: { revalidate: 86400 } }
    )
    data = res.ok ? await res.json() : { combinations: [] }
  } catch (e) {
    console.warn("Backend offline during build, skipping top-combinations fetch");
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900">
        Software Job Salary Guide — India {new Date().getFullYear()}
      </h1>
      <p className="mt-2 text-gray-500">
        Live salary data from thousands of job listings, updated daily.
      </p>
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data.combinations.map((c: any) => (
          <Link
            key={`${c.role_slug}-${c.city_slug}`}
            href={`/salaries/${c.role_slug}/${c.city_slug}`}
            className="rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-200 hover:shadow-sm transition-all block"
          >
            <p className="font-medium text-gray-900">
              {c.role_slug.replace(/-/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase())}
            </p>
            <p className="text-sm text-gray-500">
              {c.city_slug.charAt(0).toUpperCase() + c.city_slug.slice(1)}
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
