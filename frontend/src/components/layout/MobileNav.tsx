'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Users,
  MonitorPlay,
  FolderKanban,
  Film,
} from 'lucide-react';

const navigation = [
  { name: 'Home', href: '/', icon: LayoutDashboard },
  { name: 'Editor', href: '/editor', icon: Film },
  { name: 'Projects', href: '/projects', icon: FolderKanban },
  { name: 'Competitors', href: '/competitors', icon: Users },
  { name: 'Ads', href: '/ads', icon: MonitorPlay },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 px-2 py-2 safe-area-inset-bottom">
      <div className="flex justify-around">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex flex-col items-center justify-center px-3 py-1 rounded-lg transition-colors min-w-0',
                isActive ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="text-xs mt-1 truncate">{item.name}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
