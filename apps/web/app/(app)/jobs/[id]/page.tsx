import { notFound } from "next/navigation";
import { MapPin, Calendar, IndianRupee, Wifi, ExternalLink } from "lucide-react";
import { formatSalary, formatDate } from "@/lib/utils";
import type { Job } from "@/lib/types";
import type { Metadata } from "next";

// ISR — revalidate every 15 minutes
export const revalidate = 900;

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function getJob(id: string): Promise<Job | null> {
  try {
    const res = await fetch(`${API_URL}/v1/jobs/${id}`, {
      next: { revalidate: 900 },
    });
    if (!res.ok) return null;
    return res.json() as Promise<Job>;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  const job = await getJob(params.id);
  if (!job) return { title: "Job not found" };
  return {
    title: `${job.title} at ${job.company_name} — JobsIndia`,
    description: `${job.title} position at ${job.company_name}${job.location_city ? ` in ${job.location_city}` : ""}. ${job.is_remote ? "Remote." : ""}`,
  };
}

export default async function JobDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const job = await getJob(params.id);
  if (!job) notFound();

  // Resolve nested objects to flat strings for display
  const companyName = job.company_name ?? job.company?.name ?? "Unknown Company";
  const locationCity = job.location_city ?? job.location?.city ?? null;

  const jsonLd = {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    title: job.title_normalized ?? job.title,
    description: job.description,
    hiringOrganization: {
      "@type": "Organization",
      name: companyName,
    },
    jobLocation: job.is_remote
      ? { "@type": "Place", address: "Remote" }
      : {
          "@type": "Place",
          address: {
            "@type": "PostalAddress",
            addressLocality: locationCity,
            addressCountry: "IN",
          },
        },
    datePosted: job.posted_at,
    ...(job.salary_min && {
      baseSalary: {
        "@type": "MonetaryAmount",
        currency: job.currency ?? "INR",
        value: {
          "@type": "QuantitativeValue",
          minValue: job.salary_min,
          maxValue: job.salary_max ?? job.salary_min,
        },
      },
    }),
  };

  return (
    <>
      {/* JSON-LD for Google Jobs rich results */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold leading-tight">
              {job.title_normalized ?? job.title}
            </h1>
            <p className="text-lg text-muted-foreground mt-1">
              {companyName}
            </p>
          </div>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors flex-shrink-0"
          >
            Apply now
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mb-6 pb-6 border-b border-border">
          {locationCity && (
            <span className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4" />
              {locationCity}
            </span>
          )}
          {job.is_remote && (
            <span className="flex items-center gap-1.5">
              <Wifi className="w-4 h-4" />
              Remote
            </span>
          )}
          {(job.salary_min || job.salary_max) && (
            <span className="flex items-center gap-1.5">
              <IndianRupee className="w-4 h-4" />
              {formatSalary(job.salary_min, job.salary_max)}
            </span>
          )}
          <span className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4" />
            Posted {formatDate(job.posted_at)}
          </span>
        </div>

        {/* Skills */}
        {job.skills && job.skills.length > 0 && (
          <section className="mb-6" aria-label="Required skills">
            <h2 className="font-semibold text-base mb-3">Skills required</h2>
            <div className="flex flex-wrap gap-2">
              {job.skills.map((skill: string) => (
                <span
                  key={skill}
                  className="px-3 py-1 rounded-full bg-secondary text-secondary-foreground text-sm"
                >
                  {skill}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Description */}
        <section aria-label="Job description">
          <h2 className="font-semibold text-base mb-3">About this role</h2>
          <div
            className="prose prose-sm dark:prose-invert max-w-none"
            dangerouslySetInnerHTML={{
              __html: job.description ?? "No description available.",
            }}
          />
        </section>
      </div>
    </>
  );
}
