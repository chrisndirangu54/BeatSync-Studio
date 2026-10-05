"use client";

import { useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { createAccount, signInWithEmail, signInWithGoogle, watchAuth } from "@/lib/firebase";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [user,setUser]=useState<User|null|undefined>(undefined);
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [createMode,setCreateMode]=useState(false);
  const [error,setError]=useState("");

  useEffect(()=>watchAuth(setUser),[]);

  if(user===undefined) return <main className="authShell"><div className="authCard">Loading BeatSync…</div></main>;
  if(user) return <>{children}</>;

  async function emailAction(e:React.FormEvent){
    e.preventDefault(); setError("");
    try{
      if(createMode) await createAccount(email,password);
      else await signInWithEmail(email,password);
    }catch(err:any){ setError(err?.message||"Authentication failed"); }
  }

  return (
    <main className="authShell">
      <div className="authCard">
        <span className="eyebrow">BEATSYNC STUDIO</span>
        <h1>{createMode?"Create account.":"Sign in to create."}</h1>
        <p>Your projects, subscription, render usage and privileges are tied to your verified Firebase identity.</p>
        <button className="primary authButton" onClick={()=>signInWithGoogle().catch(e=>setError(e.message))}>Continue with Google</button>
        <div className="authDivider"><span>or</span></div>
        <form onSubmit={emailAction}>
          <input className="authInput" type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} required/>
          <input className="authInput" type="password" placeholder="Password" minLength={6} value={password} onChange={e=>setPassword(e.target.value)} required/>
          <button className="secondary authButton" type="submit">{createMode?"Create email account":"Sign in with email"}</button>
        </form>
        <button className="linkButton" onClick={()=>{setCreateMode(!createMode);setError("");}}>
          {createMode?"Already have an account? Sign in":"New to BeatSync? Create an account"}
        </button>
        {error&&<div className="authError">{error}</div>}
      </div>
    </main>
  );
}
