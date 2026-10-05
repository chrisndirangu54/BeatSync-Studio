"use client";

import { useEffect, useState } from "react";
import { authJSON, authRequest } from "@/lib/api";

type UserRow = {
  uid:string; email:string|null; display_name:string|null; disabled:boolean;
  email_verified:boolean; role:string; plan:string; admin:boolean; permissions:string[];
};
type RenderJob = { id:string; status:string; progress:number; owner_email?:string; plan_key?:string; };

export default function AdminPage(){
  const [users,setUsers]=useState<UserRow[]>([]);
  const [renders,setRenders]=useState<RenderJob[]>([]);
  const [providers,setProviders]=useState<Record<string,boolean>>({});
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);

  async function load(){
    setLoading(true);setError("");
    try{
      const [u,r,p]=await Promise.all([
        authJSON<UserRow[]>("/v1/admin/users"),
        authJSON<RenderJob[]>("/v1/admin/renders"),
        authJSON<Record<string,boolean>>("/v1/admin/provider-status"),
      ]);
      setUsers(u);setRenders(r);setProviders(p);
    }catch(e:any){ setError(e?.message||"Unable to load admin console"); }
    finally{ setLoading(false); }
  }
  useEffect(()=>{load();},[]);

  async function toggleDisabled(user:UserRow){
    await authRequest("/v1/admin/users/"+user.uid+"/disabled",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({disabled:!user.disabled})});
    await load();
  }

  async function promote(user:UserRow){
    await authRequest("/v1/admin/users/"+user.uid+"/role",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      role:user.admin?"user":"admin",admin:!user.admin,permissions:user.admin?[]:[
        "users.read","users.write","users.roles","auth.sessions.revoke","renders.read","renders.manage",
        "plans.read","plans.manage","billing.read","billing.manage","providers.read","providers.manage","audit.read"
      ]
    })});
    await load();
  }

  async function setPlan(user:UserRow,plan:string){
    await authRequest("/v1/admin/users/"+user.uid+"/plan",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({plan})});
    await load();
  }

  async function revoke(user:UserRow){
    await authRequest("/v1/admin/users/"+user.uid+"/revoke-sessions",{method:"POST"});
  }

  if(loading)return <main className="shell"><div className="panel">Loading admin console…</div></main>;

  return <main className="shell">
    <header className="hero"><div><span className="eyebrow">BEATSYNC ADMIN</span><h1>Platform control.</h1><p>Manage users, subscriptions, privileges, active sessions, render activity and provider readiness.</p></div><a className="secondary adminBack" href="/">Back to Studio</a></header>
    {error&&<div className="authError">{error}</div>}
    <section className="panel">
      <div className="panelTitle"><span>01</span><h2>Users & access</h2></div>
      <div className="adminTableWrap"><table className="adminTable">
        <thead><tr><th>User</th><th>Role</th><th>Plan</th><th>Status</th><th>Verified</th><th>Actions</th></tr></thead>
        <tbody>{users.map(u=><tr key={u.uid}>
          <td><b>{u.display_name||u.email||u.uid}</b><small>{u.email}</small></td>
          <td>{u.admin?"Admin":u.role}</td>
          <td><select className="adminSelect" value={u.plan||"free"} disabled={u.admin} onChange={e=>setPlan(u,e.target.value)}><option value="free">Free</option><option value="pro">Pro</option><option value="creator">Creator</option><option value="studio">Studio</option></select></td>
          <td>{u.disabled?"Disabled":"Active"}</td><td>{u.email_verified?"Yes":"No"}</td>
          <td><div className="adminActions">
            <button className="toggle" onClick={()=>toggleDisabled(u)}>{u.disabled?"Enable":"Disable"}</button>
            <button className="toggle" onClick={()=>promote(u)}>{u.admin?"Demote":"Make admin"}</button>
            {!u.admin&&<button className="toggle" onClick={()=>revoke(u)}>Revoke sessions</button>}
          </div></td>
        </tr>)}</tbody>
      </table></div>
    </section>

    <section className="grid two">
      <div className="panel"><div className="panelTitle"><span>02</span><h2>Render oversight</h2></div>
        {renders.length===0?<p className="muted">No in-memory render jobs on this API instance.</p>:renders.map(r=><div className="adminListItem" key={r.id}><b>{r.owner_email||r.id}</b><span>{r.status} · {Math.round((r.progress||0)*100)}% · {r.plan_key||"free"}</span></div>)}
      </div>
      <div className="panel"><div className="panelTitle"><span>03</span><h2>Provider readiness</h2></div>
        {Object.entries(providers).map(([name,ready])=><div className="adminListItem" key={name}><b>{name}</b><span>{ready?"Configured":"Missing"}</span></div>)}
      </div>
    </section>
  </main>;
}
