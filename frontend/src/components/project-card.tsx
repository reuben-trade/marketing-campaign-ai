'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Video,
  HardDrive,
  Layers,
  MoreVertical,
  Pencil,
  Trash2,
  Upload,
  Clock,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { Project } from '@/types/project';

interface ProjectCardProps {
  project: Project;
  onEdit?: (project: Project) => void;
  onDelete?: (project: Project) => void;
}

const statusConfig: Record<
  Project['status'],
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  draft: { label: 'Draft', variant: 'secondary' },
  processing: { label: 'Processing', variant: 'default' },
  ready: { label: 'Ready', variant: 'outline' },
  rendered: { label: 'Rendered', variant: 'default' },
};

export function ProjectCard({ project, onEdit, onDelete }: ProjectCardProps) {
  const status = statusConfig[project.status] || statusConfig.draft;
  const stats = project.stats || { videos_uploaded: 0, total_size_mb: 0, segments_extracted: 0 };

  return (
    <Card className="group relative overflow-hidden transition-all hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <Link href={`/projects/${project.id}`}>
            <CardTitle className="text-lg font-semibold hover:underline">
              {project.name}
            </CardTitle>
          </Link>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>
              Updated {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={status.variant}>{status.label}</Badge>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
                <span className="sr-only">Open menu</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/projects/${project.id}`}>
                  <Upload className="mr-2 h-4 w-4" />
                  View Project
                </Link>
              </DropdownMenuItem>
              {onEdit && (
                <DropdownMenuItem onClick={() => onEdit(project)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
              )}
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(project)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        {project.user_prompt && (
          <p className="mb-4 text-sm text-muted-foreground line-clamp-2">
            {project.user_prompt}
          </p>
        )}
        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-2">
            <Video className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm">
              <span className="font-medium">{stats.videos_uploaded}</span>
              <span className="text-muted-foreground">/{project.max_videos}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm">
              <span className="font-medium">{stats.total_size_mb.toFixed(1)}</span>
              <span className="text-muted-foreground">MB</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm">
              <span className="font-medium">{stats.segments_extracted}</span>
              <span className="text-muted-foreground"> segments</span>
            </div>
          </div>
        </div>
        {project.status === 'draft' && stats.videos_uploaded === 0 && (
          <Link href={`/projects/${project.id}`}>
            <Button variant="outline" className="mt-4 w-full" size="sm">
              <Upload className="mr-2 h-4 w-4" />
              Upload Videos
            </Button>
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
