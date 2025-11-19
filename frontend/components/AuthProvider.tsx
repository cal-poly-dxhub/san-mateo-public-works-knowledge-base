'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getCurrentUser } from '@/lib/auth';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    getCurrentUser()
      .then(() => {
        setIsAuthenticated(true);
        setIsLoading(false);
      })
      .catch(() => {
        setIsAuthenticated(false);
        setIsLoading(false);
        if (pathname !== '/login') {
          router.push('/login');
        }
      });
  }, [pathname, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated && pathname !== '/login') {
    return null;
  }

  return <>{children}</>;
}
