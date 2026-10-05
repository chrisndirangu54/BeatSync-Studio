"use client";

import { useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { logout, watchAuth } from "@/lib/firebase";
import { authJSON } from "@/lib/api";

type Me = { uid:string; email:string|null; role:string; admin:boolean; permissions:string[] };

export default function UserMenu(){
  const [user,setUser]=useState<User|null>(null);
  const [me,setMe]=useState<Me|null>(null);
  useEffect(()=>watchAuth(async u=>{
    setUser(u);
    if(u){
      try{ setMe(await authJSON<Me>("/v1/auth/me")); }catch{ setMe(null); }
    }else setMe(null);
  }),[]);

  if(!user) return null;
  return <div className="userMenu">
    <div><b>{user.displayName||user.email||"User"}</b><span>{me?.admin?"Platform Admin":me?.role||"User"}</span></div>
    <button className="toggle" onClick={()=>logout()}>Sign out</button>
  </div>
}
