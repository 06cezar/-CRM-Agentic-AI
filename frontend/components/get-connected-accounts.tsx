"use client";

import { useState, useEffect } from "react";

// Definim structura unui cont asa cum o asteptam de la backend
interface ConnectedAccount {
  id: number;
  email: string;
  provider: string;
  is_watching: boolean; // Presupunem ca backend-ul ne trimite acest status
}

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Preia conturile cand componenta se incarca
  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      // Inlocuieste cu ruta ta reala din backend
      const res = await fetch("http://localhost:8000/api/auth/google/get_connected_accounts", {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setAccounts(data);
      }
    } catch (error) {
      console.error("Eroare la preluarea conturilor:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWatchStatus = async (accountId: number, currentStatus: boolean) => {
  const newStatus = !currentStatus; // Ce vrem să devină

  // Update optimist în UI
  setAccounts((prev) =>
    prev.map((acc) =>
      acc.id === accountId ? { ...acc, is_watching: newStatus } : acc
    )
  );

  try {
    const res = await fetch(`http://localhost:8000/api/gmail/watch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        account_id: accountId,
        active: newStatus, // Trimitem true pentru start, false pentru stop
      }),
    });

    if (!res.ok) throw new Error("Serverul a respins solicitarea");

    // Sincronizăm statusul persistent în baza de date folosind noul endpoint
    await fetch(`http://localhost:8000/api/gmail/set-status`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        account_id: accountId,
        active: newStatus,
      }),
    });
    
  } catch (error) {
    console.error("Eroare la schimbarea statusului:", error);
    // Revenim la statusul vechi în caz de eroare
    setAccounts((prev) =>
      prev.map((acc) =>
        acc.id === accountId ? { ...acc, is_watching: currentStatus } : acc
      )
    );
  }
  };

  const disconnectAccount = async (accountId: number) => {
  if (!confirm("Sigur vrei sa deconectezi acest cont? Monitorizarea se va opri definitiv.")) return;

  try {
    const res = await fetch(`http://localhost:8000/api/auth/google/disconnect/${accountId}`, {
      method: "DELETE",
      credentials: "include",
    });

    if (res.ok) {
      setAccounts((prev) => prev.filter((acc) => acc.id !== accountId));
    } else {
      throw new Error("Eroare la deconectare");
    }
  } catch (error) {
    console.error("Eroare la deconectarea contului:", error);
  }
  };

  return (
  <div className="max-w-3xl mx-auto p-6 space-y-8">      <div>
        <h1 className="text-2xl font-bold text-gray-900">Setari Cont</h1>
        <p className="text-gray-500 mt-1">Gestioneaza conturile conectate si preferintele de sincronizare.</p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-medium leading-6 text-gray-900">Conturi de Email Conectate</h3>
          <a 
            href="http://localhost:8000/api/auth/google/login" 
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
          >
            + Conecteaza cont nou
          </a>
        </div>
        
        <div className="px-6 py-5">
          {isLoading ? (
            <div className="text-center text-gray-500 py-4">Se incarca conturile...</div>
          ) : accounts.length === 0 ? (
            <div className="text-center text-gray-500 py-4">Nu ai niciun cont conectat momentan.</div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {accounts.map((account) => (
                <li key={account.id} className="py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Iconita generica pentru Google */}
                    <div className="flex-shrink-0 size-10 rounded-full bg-gray-100 flex items-center justify-center">
                      <span className="text-gray-500 font-bold text-lg">G</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{account.email}</p>
                      <p className="text-sm text-gray-500 capitalize">{account.provider}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-500">
                      {account.is_watching ? "Monitorizare Activa" : "Monitorizare Oprita"}
                    </span>
                    
                    {/* Toggle Button (Switch) creat cu Tailwind */}
                    <button
                      type="button"
                      onClick={() => toggleWatchStatus(account.id, account.is_watching)}
                      className={`${
                        account.is_watching ? "bg-blue-600" : "bg-gray-200"
                      } relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2`}
                      role="switch"
                      aria-checked={account.is_watching}
                    >
                      <span className="sr-only">Activeaza monitorizarea</span>
                      <span
                        aria-hidden="true"
                        className={`${
                          account.is_watching ? "translate-x-5" : "translate-x-0"
                        } pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
                      />
                    </button>

                    <button
                      onClick={() => disconnectAccount(account.id)}
                      className="text-xs text-red-600 hover:text-red-800 font-medium ml-2"
                    >
                      Deconectează
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}