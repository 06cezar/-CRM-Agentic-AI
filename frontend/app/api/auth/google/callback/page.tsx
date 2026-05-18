"use client";
import { useEffect, Suspense, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function GoogleCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const hasFetched = useRef(false);

  // Functie mica pentru a extrage un cookie dupa nume
  const getCookie = (name: string) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(";").shift();
    return null;
  };

  useEffect(() => {
    const code = searchParams.get("code");
    
    if (code && !hasFetched.current) {
      hasFetched.current = true;
      

      // Adaugam si credentials: 'include' ca browserul sa trimita automat si cookies la backend
      fetch(`http://localhost:8000/api/auth/google/callback?code=${code}`, {
        method: 'GET',
        credentials: 'include' // Evitam erori de CORS pe localhost cand trimitem headere de Authorization manual
      })
        .then(async (res) => {
          if (!res.ok) {
             const errorData = await res.json();
             throw new Error(errorData.detail || "Eroare de la server");
          }
          return res.json();
        })
        .then((data) => {
          console.log("Succes! Logat cu Google:", data);
          router.push("/settings?connected=true");
        })
        .catch((err) => {
          console.error("Eroare:", err);
          const msg = err instanceof Error ? encodeURIComponent(err.message) : "google_error";
          router.push(`/settings?error=${msg}`);
        });
    }
  }, [searchParams, router]);

  return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-700">Se proceseaza autentificarea cu Google...</h2>
        <p className="text-gray-500 mt-2">Te rugam sa astepti cateva secunde.</p>
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center">Se incarca...</div>}>
      <GoogleCallbackContent />
    </Suspense>
  );
}