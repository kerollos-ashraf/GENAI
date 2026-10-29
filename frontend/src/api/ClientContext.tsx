/** Dependency injection for the API gateway: the app gets the real client, tests a fake. */
import { createContext, useContext, type ReactNode } from "react";
import { OmniCareClient } from "./client";

const ClientContext = createContext<OmniCareClient>(new OmniCareClient());

export function ClientProvider({
  client,
  children,
}: {
  client: OmniCareClient;
  children: ReactNode;
}) {
  return <ClientContext.Provider value={client}>{children}</ClientContext.Provider>;
}

export function useClient(): OmniCareClient {
  return useContext(ClientContext);
}
