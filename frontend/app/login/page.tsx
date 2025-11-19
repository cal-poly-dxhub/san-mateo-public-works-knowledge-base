'use client';

import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { getCurrentUser } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    getCurrentUser()
      .then(() => router.push('/'))
      .catch(() => {});
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-center mb-8">Project Management System</h1>
        <Authenticator
          signUpAttributes={['email', 'given_name', 'family_name']}
          hideSignUp={true}
        >
          {({ signOut, user }) => {
            if (user) {
              router.push('/');
            }
            return null;
          }}
        </Authenticator>
      </div>
    </div>
  );
}
