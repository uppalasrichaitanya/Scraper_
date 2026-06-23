import { notFound } from "next/navigation"
import { Metadata } from "next"
import { SalaryRangeBar } from "@/components/salary/SalaryRangeBar"

export const revalidate = 86400

interface Props {
  params: { role: string; city: string }
}

function slugToLabel(slug: string): string {
  return slug.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const role = slugToLabel(params.role)
  const city = slugToLabel(params.city)
  const year = new Date().getFullYear()
  return {
    title: `${role} Salary in ${city} ${year} — Live Data`,
    description:
      `Average ${role} salary in ${city} ${year}: ` +
      `percentile breakdown from live job listings. Updated daily.`,
    openGraph: {
      title: `${role} Salary in ${city} ${year}`,
      description: `Live salary data for ${role} jobs in ${city}.`,
    },
  }
}

export async function generateStaticParams() {
  try {
    const apiUrl = [process.env.INTERNAL_API_URL, process.env.NEXT_PUBLIC_API_URL, "http://127.0.0.1:8000"].find(u => u && u !== "undefined");
    const res = await fetch(
      `${apiUrl}/v1/salaries/top-combinations`,
      { next: { revalidate: 86400 } }
    )
    if (!res.ok) return []
    const data = await res.json()
    return (data.combinations ?? []).map((c: { role_slug: string; city_slug: string }) => ({
      role: c.role_slug,
      city: c.city_slug,
    }))
  } catch {
    return []
  }
}

async function getSalaryData(role: string, city: string) {
  try {
    const apiUrl = [process.env.INTERNAL_API_URL, process.env.NEXT_PUBLIC_API_URL, "http://127.0.0.1:8000"].find(u => u && u !== "undefined");
    const res = await fetch(
      `${apiUrl}/v1/salaries/${role}/${city}`,
      { next: { revalidate: 86400 } }
    )
    if (!res.ok) return null
    return await res.json()
  } catch (e) {
    console.warn(`Backend offline during build, skipping getSalaryData for ${role}/${city}`);
    return null;
  }
}

export default async function SalaryPage({ params }: Props) {
  const data = await getSalaryData(params.role, params.city)

  // Guard: don't render misleading pages with thin data
  if (!data || data.sample_size < 30) notFound()

  const role = slugToLabel(params.role)
  const city = slugToLabel(params.city)
  const year = new Date().getFullYear()
  const toL = (v: number) => `₹${(v / 100000).toFixed(1)}L`

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      {/* SEO: structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Article",
            headline: `${role} Salary in ${city} ${year}`,
            dateModified: new Date().toISOString(),
          }),
        }}
      />

      <h1 className="text-3xl font-bold tracking-tight text-gray-900">
        {role} Salary in {city} ({year})
      </h1>
      <p className="mt-2 text-sm text-gray-500">
        Based on{" "}
        <span className="font-medium text-gray-700">
          {data.sample_size.toLocaleString("en-IN")} live job listings
        </span>{" "}
        · Updated daily
      </p>

      {/* Percentile cards */}
      <div className="mt-8 grid grid-cols-3 gap-4">
        {[
          { label: "Entry (25th %ile)", value: toL(data.p25) },
          { label: "Median", value: toL(data.median), highlight: true },
          { label: "Senior (75th %ile)", value: toL(data.p75) },
        ].map(({ label, value, highlight }) => (
          <div
            key={label}
            className={`rounded-xl border p-5 text-center ${
              highlight
                ? "border-blue-200 bg-blue-50"
                : "border-gray-200 bg-white"
            }`}
          >
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
              {label}
            </p>
            <p
              className={`mt-2 text-2xl font-bold ${
                highlight ? "text-blue-600" : "text-gray-900"
              }`}
            >
              {value}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">per annum</p>
          </div>
        ))}
      </div>

      {/* Visual bar */}
      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
        <SalaryRangeBar p25={data.p25} median={data.median} p75={data.p75} />
      </div>

      {/* CTA — links to search */}
      <div className="mt-8 rounded-xl border border-blue-100 bg-blue-50 px-6 py-5">
        <p className="font-semibold text-blue-900">
          {data.open_positions ?? data.sample_size} {role} jobs open in {city} right now
        </p>
        <p className="mt-1 text-sm text-blue-700">
          Apply to live listings with salary data.
        </p>
        <a
          href={`/search?q=${encodeURIComponent(params.role.replace(/-/g, " "))}&location=${params.city}`}
          className="mt-3 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Browse {role} jobs in {city} →
        </a>
      </div>

      {/* FAQ — boosts SEO long-tail */}
      <section className="mt-12">
        <h2 className="text-xl font-semibold text-gray-900">
          Frequently Asked Questions
        </h2>
        <div className="mt-4 space-y-4">
          <Faq
            q={`What is the average ${role} salary in ${city}?`}
            a={`The median ${role} salary in ${city} is ${toL(data.median)} per annum, based on ${data.sample_size.toLocaleString("en-IN")} job listings.`}
          />
          <Faq
            q={`What is the salary range for ${role} in ${city}?`}
            a={`${role} salaries in ${city} typically range from ${toL(data.p25)} (entry level) to ${toL(data.p75)} (senior level).`}
          />
        </div>
      </section>
    </main>
  )
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <details className="rounded-lg border border-gray-200 bg-white px-5 py-4">
      <summary className="cursor-pointer text-sm font-medium text-gray-900">{q}</summary>
      <p className="mt-2 text-sm text-gray-600">{a}</p>
    </details>
  )
}
