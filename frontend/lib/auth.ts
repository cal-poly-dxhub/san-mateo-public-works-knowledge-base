import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID!,
      userPoolClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID!,
      region: process.env.NEXT_PUBLIC_AWS_REGION!,
      loginWith: {
        email: true,
      },
    },
  },
});

export { signIn, signOut, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
