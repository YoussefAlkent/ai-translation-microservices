"use client";

import SuperTokens from "supertokens-auth-react";
import { frontendConfig } from "@/config/supertokens";
import { useEffect } from "react";

if (typeof window !== "undefined") {
  SuperTokens.init(frontendConfig());
}

export default function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (typeof window !== "undefined") {
      SuperTokens.init(frontendConfig());
    }
  }, []);

  return <>{children}</>;
}
