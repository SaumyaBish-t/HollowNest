"use client";

import NexusApp from "@/components/NexusApp";
import { useParams } from "next/navigation";

export default function SessionPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : null;
  
  return <NexusApp initialSessionId={id} />;
}
