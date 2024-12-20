import SuperTokens from "supertokens-auth-react";
import EmailPassword from "supertokens-auth-react/recipe/emailpassword";
import Session from "supertokens-auth-react/recipe/session";
import type { SuperTokensConfig } from "supertokens-auth-react/lib/build/types";

const SERVER_DOMAIN = process.env.NEXT_PUBLIC_SERVER_DOMAIN || "http://localhost:8000";

export const frontendConfig = (): SuperTokensConfig => {
  return {
    appInfo: {
      appName: "Cloud Project",
      apiDomain: SERVER_DOMAIN,
      websiteDomain: "http://localhost:4200",
      apiBasePath: "/auth",
      websiteBasePath: "/auth",
    },
    recipeList: [
      EmailPassword.init({
        signInAndUpFeature: {
          signUpForm: {
            formFields: [
              { 
                id: "email",
                label: "Email Address",
              }, 
              { 
                id: "password",
                label: "Password",
              }
            ],
          },
        },
      }),
      Session.init(),
    ],
  };
};