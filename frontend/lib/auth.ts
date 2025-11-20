import { Amplify } from 'aws-amplify';

let configured = false;

export const configureAmplify = () => {
  if (configured) return;
  
  const config = typeof window !== 'undefined' 
    ? (window as any).__RUNTIME_CONFIG__ 
    : null;

  if (config?.userPoolId && config?.userPoolClientId && config?.region) {
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
    configured = true;
  }
};

export { signIn, signOut, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
