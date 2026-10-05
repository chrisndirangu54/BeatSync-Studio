"use client";

import { useEffect, useState } from "react";
import { authJSON, authRequest } from "@/lib/api";

type UserRow = {
  uid:string; email:string|null; display_name:string|null; disabled:boolean;
  email_verified:boolean; role:string; admin:boolean; permissions:string[];
};

export default function AdminPage(){
  const [users,setUsers]=useState<UserRow[]>([]);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);

  async function load(){
    setLoading(true);setError("");
    try{ setUsers(await authJSON<UserRow[]>("/v1/admin/users")); }
    catch(e:any){ setError(e?.message||"Unable to load admin console"); }
    finally{ setLoading(false); }
  }
  useEffect(()=>{load();},[]);

  async function toggleDisabled(user:UserRow){
    await authRequest("/v1/admin/users/"+user.uid+"/disabled",{
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({disabled:!user.disabled}),
    });
    await load();
  }

  async function promote(user:UserRow){
    await authRequest("/v1/admin/users/"+user.uid+"/role",{
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        role:user.admin?"user":"admin",
        admin:!user.admin,
        permissions:user.admin?[]:[
          "users.read","users.write","users.roles","auth.sessions.revoke",
          "renders.read","renders.manage","plans.read","plans.manage",
          "billing.read","billing.manage","providers.read","providers.manage","audit.read"
        ]
      }),
    });
    await load();
  }

  if(loading)return <main className="shell"><div className="panel">Loading admin console…</div></main>;

  return <main className="shell">
    <header className="hero"><div><span className="eyebrow">BEATSYNC ADMIN</span><h1>Platform control.</h1><p>Manage accounts, roles, access and security sessions.</p></div></header>
    {error&&<div className="authError">{error}</div>}
    <section className="panel">
      <div className="panelTitle"><span>01</span><h2>Users</h2></div>
      <div className="adminTableWrap">
        <table className="adminTable">
          <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Verified</th><th>Actions</th></tr></thead>
          <tbody>{users.map(u=><tr key={u.uid}>
            <td><b>{u.display_name||u.email||u.uid}</b><small>{u.email}</small></td>
            <td>{u.admin?"Admin":u.role}</td>
            <td>{u.disabled?"Disabled":"Active"}</td>
            <td>{u.email_verified?"Yes":"No"}</td>
            <td><div className="adminActions">
              <button className="toggle" onClick={()=>toggleDisabled(u)}>{u.disabled?"Enable":"Disable"}</button>
              <button className="toggle" onClick={()=>promote(u)}>{u.admin?"Demote":"Make admin"}</button>
            </div></td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>
  </main>;
}
