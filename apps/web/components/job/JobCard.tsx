import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { MapPin, Clock, IndianRupee, Wifi } from "lucide-react";
import { formatSalary, timeAgo } from "@/lib/utils";
import type { Job } from "@/lib/types";

interface JobCardProps {
  job: Job;
}

export default function JobCard({ job }: JobCardProps) {
  const displayTitle = job.title_normalized ?? job.title;
  const displayDate = job.updated_at;
  // Resolve flat fields from nested API objects
  const companyName = job.company_name ?? job.company?.name ?? "Unknown Company";
  const locationCity = job.location_city ?? job.location?.city ?? null;

  return (
    <Link href={`/jobs/${job.id}`}>
      <Card className="hover:shadow-md transition-all duration-200 cursor-pointer group border border-border/50 hover:border-primary/30">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate transition-colors">
                {displayTitle}
              </h3>
              <p className="text-sm text-muted-foreground mt-0.5">
                {companyName}
              </p>
            </div>
            {job.is_remote && (
              <Badge
                variant="secondary"
                className="flex-shrink-0 gap-1"
              >
                <Wifi className="w-3 h-3" />
                Remote
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 mt-3 text-sm text-muted-foreground">
            {locationCity && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" />
                {locationCity}
              </span>
            )}
            {(job.salary_min || job.salary_max) && (
              <span className="flex items-center gap-1">
                <IndianRupee className="w-3.5 h-3.5" />
                {formatSalary(job.salary_min, job.salary_max)}
              </span>
            )}
            <span className="flex items-center gap-1 ml-auto">
              <Clock className="w-3.5 h-3.5" />
              {timeAgo(displayDate)}
            </span>
          </div>

          {job.skills && job.skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {job.skills.slice(0, 5).map((skill) => (
                <Badge key={skill} variant="outline" className="text-xs">
                  {skill}
                </Badge>
              ))}
              {job.skills.length > 5 && (
                <Badge variant="outline" className="text-xs text-muted-foreground">
                  +{job.skills.length - 5}
                </Badge>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

export function JobCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <div className="flex gap-3">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-5 w-16 rounded-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
