'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import type { ProjectCreate, Project } from '@/types/project';

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: ProjectCreate) => Promise<void>;
  isLoading?: boolean;
  editProject?: Project | null;
}

export function CreateProjectDialog({
  open,
  onOpenChange,
  onSubmit,
  isLoading = false,
  editProject = null,
}: CreateProjectDialogProps) {
  const [name, setName] = useState(editProject?.name || '');
  const [userPrompt, setUserPrompt] = useState(editProject?.user_prompt || '');
  const [errors, setErrors] = useState<{ name?: string }>({});

  const isEditing = !!editProject;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    const newErrors: { name?: string } = {};
    if (!name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (name.length > 200) {
      newErrors.name = 'Project name must be 200 characters or less';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});

    const data: ProjectCreate = {
      name: name.trim(),
    };

    if (userPrompt.trim()) {
      data.user_prompt = userPrompt.trim();
    }

    await onSubmit(data);

    // Reset form if not editing
    if (!isEditing) {
      setName('');
      setUserPrompt('');
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Reset form when closing
      if (!isEditing) {
        setName('');
        setUserPrompt('');
      }
      setErrors({});
    } else if (editProject) {
      // Populate form when opening in edit mode
      setName(editProject.name);
      setUserPrompt(editProject.user_prompt || '');
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEditing ? 'Edit Project' : 'Create New Project'}</DialogTitle>
            <DialogDescription>
              {isEditing
                ? 'Update your project details.'
                : 'Start a new ad creation project. You can upload videos and select inspiration after creating the project.'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">
                Project Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                placeholder="e.g., Summer Sale Ad Campaign"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (errors.name) setErrors({});
                }}
                disabled={isLoading}
                aria-invalid={!!errors.name}
              />
              {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="userPrompt">
                Creative Direction <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Textarea
                id="userPrompt"
                placeholder="e.g., Focus on the 50% discount, show product in use, target young professionals"
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                disabled={isLoading}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Describe what you want to highlight in your ad. This helps guide the AI during
                generation.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditing ? 'Save Changes' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
