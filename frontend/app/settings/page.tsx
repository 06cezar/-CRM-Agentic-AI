"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ConnectedAccounts from "@/components/get-connected-accounts";
import { CommandHeader } from "@/components/command-header";
import { X } from "lucide-react";

export default function SettingsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // State-uri noi pentru verificarea conexiunii
  const [isGoogleConnected, setIsGoogleConnected] = useState(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState(true);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Verificam daca userul este deja conectat cand se incarca pagina
  useEffect(() => {
    const fetchUserStatus = async () => {
      try {
        // Apeleaza ruta ta care returneaza datele userului curent (ex: /api/users/me)
        const response = await fetch(`${apiUrl}/auth/me`, {
          method: "GET",
          credentials: "include" // Ca sa trimita cookie-ul de sesiune
        });

        if (response.ok) {
          const userData = await response.json();
          // Verificam daca backend-ul ne spune ca are token-ul (adapteaza cheia daca o trimiti altfel din FastAPI)
          if (userData.google_refresh_token) {
            setIsGoogleConnected(true);
          }
        }
      } catch (err) {
        console.error("Eroare la preluarea statusului Google:", err);
      } finally {
        setIsCheckingStatus(false);
      }
    };

    fetchUserStatus();
  }, [apiUrl]);

  const handleGoogleConnect = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/auth/google/login`, {
        method: "GET",
        credentials: "include" 
      });

      if (!response.ok) {
        throw new Error("Nu am putut contacta serverul. Verifica daca backend-ul ruleaza.");
      }

      const data = await response.json();

      if (data.auth_url) {
        window.location.href = data.auth_url;
      } else {
        throw new Error("URL-ul de autentificare lipseste din raspunsul serverului.");
      }
    } catch (err: any) {
      console.error("Eroare la conectarea cu Google:", err);
      setError(err.message || "A aparut o eroare la initierea autentificarii.");
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    // Aici poti face un fetch catre un endpoint de deconectare (ex: DELETE /api/auth/google/disconnect)
    // care sa stearga google_refresh_token din baza de date
    alert("Functionalitatea de deconectare urmeaza sa fie implementata in backend.");
  };

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <CommandHeader />
      <main className="flex-1 p-8 max-w-4xl mx-auto w-full">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Setari Platforma</h1>
            <p className="text-gray-600">
              Gestioneaza integrarile si preferintele contului tau de freelancer.
            </p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="p-2 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            aria-label="Închide setările"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Integrari</h2>
          
          <div className="flex items-center justify-between border border-gray-100 rounded-md p-4 bg-gray-50">
            <div>
              <h3 className="font-medium text-gray-900">Google Workspace (Gmail)</h3>
              <p className="text-sm text-gray-500 mt-1">
                Conecteaza-ti contul de Gmail pentru a sincroniza mesajele clientilor direct in CRM.
              </p>
            </div>
            
            {/* Partea de butoane conditionata */}
            {isCheckingStatus ? (
              <div className="px-4 py-2 text-sm text-gray-500">Se verifica...</div>
            ) : isGoogleConnected ? (
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-green-600 flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Conectat
                </span>
                <button
                  onClick={handleDisconnect}
                  className="px-3 py-1.5 text-sm rounded-md font-medium text-gray-600 border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  Deconecteaza
                </button>
              </div>
            ) : (
              <button
                onClick={handleGoogleConnect}
                disabled={isLoading}
                className={`px-4 py-2 rounded-md font-medium text-white transition-colors flex items-center gap-2
                  ${isLoading 
                    ? "bg-blue-400 cursor-not-allowed" 
                    : "bg-blue-600 hover:bg-blue-700 active:bg-blue-800"
                  }`}
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Se conecteaza...
                  </>
                ) : (
                  "Conecteaza Gmail"
                )}
              </button>
            )}
          </div>
            <ConnectedAccounts />
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm">
              {error}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}