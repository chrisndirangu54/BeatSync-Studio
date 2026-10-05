"use client";

import { useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { signInWithEmail, signInWithGoogle, watchAuth } from "@/lib/firebase";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [user,setUser]=useState<User|null|undefined>(undefined);
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [error,setError]=useState("");

  useEffect(()=>watchAuth(setUser),[]);

  if(user===undefined) return <main className="authShell"><div className="authCard">Loading BeatSync…</div></main>;
  if(user) return <>{children}</>;

  async function emailLogin(e:React.FormEvent){
    e.preventDefault(); setError("");
    try{ await signInWithEmail(email,password); }
    catch(err:any){ setError(err?.message||"Sign in failed"); }
  }

  return (
    <main className="authShell">
      <div className="authCard">
        <span className="eyebrow">BEATSYNC STUDIO</span>
        <h1>Sign in to create.</h1>
        <p>Your projects, render usage and admin privileges are tied to your verified Firebase identity.</p>
        <button className="primary authButton" onClick={()=>signInWithGoogle().catch(e=>setError(e.message))}>Continue with Google</button>
        <div className="authDivider"><span>or</span></div>
        <form onSubmit={emailLogin}>
          <input className="authInput" type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} required/>
          <input className="authInput" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} required/>
          <button className="secondary authButton" type="submit">Sign in with email</button>
        </form>
        {error&&<div className="authError">{error}</div>}
      </div>
    </main>
  );
}
