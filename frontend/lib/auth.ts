import { Amplify } from 'aws-amplify';

// Runtime configuration - read from environment or window
const getConfig = () => {
  if (typeof window !== 'undefined') {
    // Browser - check window object first (for runtime config)
    return {
      userPoolId: (window as any).__RUNTIME_CONFIG__?.userPoolId || process.env.NEXT_PUBLIC_USER_POOL_ID,
      userPoolClientId: (window as any).__RUNTIME_CONFIG__?.userPoolClientId || process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID,
      region: (window as any).__RUNTIME_CONFIG__?.region || process.env.NEXT_PUBLIC_AWS_REGION,
    };
  }
  // Server - use env vars
  return {
    userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID,
    userPoolClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID,
    region: process.env.NEXT_PUBLIC_AWS_REGION,
  };
};

const config = getConfig();

if (config.userPoolId && config.userPoolClientId && config.region) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.userPoolId,
        userPoolClientId: config.userPoolClientId,
        region: config.region,
        loginWith: {
          email: true,
        },
      },
    },
  });
}

export { signIn, signOut, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
