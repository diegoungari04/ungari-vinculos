"""
Ungari Vínculos: diagnóstico de vínculos organizacionais e cultura.
API FastAPI + SPA estática.
"""
import os
import json
import secrets
import hashlib
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from . import instrument as ins

ROOT = Path(__file__).resolve().parent.parent
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8010").rstrip("/")
SESSION_DAYS = 7
MIN_GROUP = 3  # tamanho mínimo de grupo para agregados anônimos (área/empresa)

ROLE_RANK = {"colaborador": 0, "gestor": 1, "admin": 2, "master": 3}
ROLE_LABEL = {"colaborador": "Colaborador", "gestor": "Gestor", "admin": "Admin", "master": "Master"}

app = FastAPI(title="Ungari Vínculos", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


# ─── Senhas e sessão ──────────────────────────────────────────────────────────

def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 310000)
    return f"pbkdf2${salt.hex()}${h.hex()}"


def check_pw(pw: str, stored: Optional[str]) -> bool:
    if not stored:
        return False
    try:
        _, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 310000)
        return secrets.compare_digest(calc.hex(), h)
    except Exception:
        return False


def current_user(request: Request) -> dict:
    sid = request.cookies.get("sid")
    if not sid:
        raise HTTPException(401, "Faça login para continuar.")
    s = db.q("SELECT * FROM sessions WHERE token=?", (sid,), one=True)
    if not s or s["expires"] < datetime.utcnow().isoformat():
        raise HTTPException(401, "Sessão expirada. Faça login novamente.")
    u = db.q("SELECT * FROM users WHERE id=? AND active=1", (s["user_id"],), one=True)
    if not u:
        raise HTTPException(401, "Usuário inativo.")
    return u


def require(request: Request, min_role: str) -> dict:
    u = current_user(request)
    if ROLE_RANK[u["role"]] < ROLE_RANK[min_role]:
        raise HTTPException(403, "Você não tem permissão para esta ação.")
    return u


def public_user(u: dict) -> dict:
    keys = ("id", "name", "email", "role", "company_id", "area_id", "manager_id", "job_title", "active")
    out = {k: u.get(k) for k in keys}
    out["role_label"] = ROLE_LABEL[u["role"]]
    out["pending_invite"] = bool(u.get("invite_token")) and not u.get("password_hash")
    return out


# ─── Escopo de visibilidade ───────────────────────────────────────────────────

def subtree_ids(user_id: int) -> List[int]:
    rows = db.q("""
        WITH RECURSIVE t(id) AS (
          SELECT id FROM users WHERE manager_id=?
          UNION SELECT u.id FROM users u JOIN t ON u.manager_id=t.id
        ) SELECT id FROM t""", (user_id,))
    return [r["id"] for r in rows]


def company_scope(viewer: dict, company_id: Optional[int]) -> int:
    """Empresa sobre a qual o viewer age. Master escolhe; demais ficam na própria."""
    if viewer["role"] == "master":
        if company_id:
            return int(company_id)
        first = db.q("SELECT id FROM companies ORDER BY id LIMIT 1", one=True)
        if not first:
            raise HTTPException(400, "Cadastre uma empresa primeiro.")
        return first["id"]
    return viewer["company_id"]


def can_view_user(viewer: dict, target_id: int) -> bool:
    if viewer["id"] == target_id or viewer["role"] == "master":
        return True
    return target_id in subtree_ids(viewer["id"])


def manageable(viewer: dict, target: dict) -> bool:
    if viewer["role"] == "master":
        return True
    return viewer["role"] == "admin" and target["company_id"] == viewer["company_id"] and target["role"] != "master"


# ─── Instrumento ──────────────────────────────────────────────────────────────

def active_instrument() -> dict:
    r = db.q("SELECT * FROM instruments WHERE active=1 ORDER BY id DESC LIMIT 1", one=True)
    return {"id": r["id"], "data": json.loads(r["data"]), "created_at": r["created_at"], "note": r["note"]}


def instrument_by_id(iid: int) -> dict:
    r = db.q("SELECT * FROM instruments WHERE id=?", (iid,), one=True)
    return json.loads(r["data"])


def validate_instrument(d: dict):
    if not isinstance(d.get("likert"), list) or not isinstance(d.get("culture"), list):
        raise HTTPException(400, "Estrutura inválida.")
    ids = set()
    count = {"CO": 0, "CN": 0, "EN": 0}
    for it in d["likert"]:
        if it.get("bond") not in count or not str(it.get("text", "")).strip() or not it.get("id"):
            raise HTTPException(400, f"Item inválido: {it.get('id')}")
        if it["id"] in ids:
            raise HTTPException(400, f"Código repetido: {it['id']}")
        ids.add(it["id"])
        count[it["bond"]] += 1
    for b, n in count.items():
        if n < 2:
            raise HTTPException(400, f"Cada vínculo precisa de pelo menos 2 itens ({ins.BONDS[b]['name']}).")
    for el in d["culture"]:
        if el.get("level") not in ins.LEVELS or set(el.get("options", {}).keys()) != {"CO", "CN", "EN"}:
            raise HTTPException(400, f"Bloco de cultura inválido: {el.get('id')}")
        if el["id"] in ids:
            raise HTTPException(400, f"Código repetido: {el['id']}")
        ids.add(el["id"])
    c = d.get("cutoffs", {})
    if not (1 < float(c.get("high", 4)) < 6):
        raise HTTPException(400, "Ponto de corte deve ficar entre 1 e 6.")


# ─── E-mail (opcional) ────────────────────────────────────────────────────────

def send_mail(to: str, subject: str, body: str) -> bool:
    host, user, pw = os.environ.get("SMTP_HOST"), os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if not (host and user and pw):
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, f"Ungari Vínculos <{user}>", to
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception:
        return False


def invite_link(u: dict) -> str:
    return f"{APP_BASE_URL}/#/convite/{u['invite_token']}"


# ─── Resultados ───────────────────────────────────────────────────────────────

def results_for(user_ids: List[int], campaign_id: Optional[int] = None) -> Dict[int, dict]:
    if not user_ids:
        return {}
    ph = ",".join("?" * len(user_ids))
    args = list(user_ids)
    extra = ""
    if campaign_id:
        extra = " AND a.campaign_id=?"
        args.append(campaign_id)
    rows = db.q(f"""SELECT a.user_id, a.result, a.completed_at, a.campaign_id, c.name AS campaign
                    FROM assignments a JOIN campaigns c ON c.id=a.campaign_id
                    WHERE a.status='concluida' AND a.user_id IN ({ph}){extra}
                    ORDER BY a.completed_at""", args)
    out = {}
    for r in rows:  # o mais recente sobrescreve
        out[r["user_id"]] = {"result": json.loads(r["result"]), "completed_at": r["completed_at"],
                             "campaign": r["campaign"], "campaign_id": r["campaign_id"]}
    return out


def aggregate(results: List[dict]) -> dict:
    n = len(results)
    if not n:
        return {"n": 0}
    bonds = {b: round(sum(r["bonds"][b] for r in results) / n, 2) for b in ("CO", "CN", "EN")}
    profiles = {}
    for r in results:
        profiles[r["profile"]] = profiles.get(r["profile"], 0) + 1
    culture = {b: round(sum(r["culture_share"].get(b, 0) for r in results) / n, 1) for b in ("CO", "CN", "EN")}
    levels = {}
    for l in ins.LEVELS:
        rs = [r["levels"][l] for r in results if l in r.get("levels", {})]
        if rs:
            levels[l] = {"share": {b: round(sum(x["share"][b] for x in rs) / len(rs), 1) for b in ("CO", "CN", "EN")},
                         "intensity": round(sum(x["intensity"] for x in rs) / len(rs), 1)}
    elements = {}
    for r in results:
        for eid, e in r.get("elements", {}).items():
            d = elements.setdefault(eid, {"name": e["name"], "level": e["level"], "via": {"CO": 0, "CN": 0, "EN": 0}, "presence": []})
            d["via"][e["via"]] += 1
            d["presence"].append(e["presence"])
    for d in elements.values():
        d["presence"] = round((sum(d["presence"]) / len(d["presence"]) - 1) / 3 * 100, 1)
    mean_profile, _ = ins.classify(bonds, active_instrument()["data"].get("cutoffs", {}))
    dominant = max(profiles, key=profiles.get)
    return {"n": n, "bonds": bonds, "bonds100": {b: ins.to100(v) for b, v in bonds.items()},
            "profiles": profiles, "dominant": dominant, "mean_profile": mean_profile,
            "culture_share": culture, "levels": levels, "elements": elements}


# ─── Modelos ──────────────────────────────────────────────────────────────────

class LoginIn(BaseModel):
    email: str
    password: str


class InviteIn(BaseModel):
    password: str


class PwIn(BaseModel):
    current: str
    new: str


class PersonIn(BaseModel):
    name: str
    email: str
    role: str = "colaborador"
    area_id: Optional[int] = None
    manager_id: Optional[int] = None
    job_title: Optional[str] = None
    company_id: Optional[int] = None
    active: Optional[bool] = True


class AreaIn(BaseModel):
    name: str
    company_id: Optional[int] = None


class CompanyIn(BaseModel):
    name: str


class CampaignIn(BaseModel):
    name: str
    deadline: Optional[str] = None
    company_id: Optional[int] = None
    area_ids: Optional[List[int]] = None
    user_ids: Optional[List[int]] = None


class SubmitIn(BaseModel):
    likert: Dict[str, int]
    rank: Dict[str, List[str]]
    presence: Dict[str, int]


class InstrumentIn(BaseModel):
    data: dict
    note: Optional[str] = None


# ─── Autenticação ─────────────────────────────────────────────────────────────

@app.post("/api/login")
def login(body: LoginIn, response: Response):
    u = db.q("SELECT * FROM users WHERE lower(email)=lower(?) AND active=1", (body.email.strip(),), one=True)
    if not u or not check_pw(body.password, u["password_hash"]):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    tok = secrets.token_urlsafe(32)
    db.x("INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)",
         (tok, u["id"], (datetime.utcnow() + timedelta(days=SESSION_DAYS)).isoformat()))
    response.set_cookie("sid", tok, httponly=True, samesite="lax", max_age=SESSION_DAYS * 86400,
                        secure=APP_BASE_URL.startswith("https"))
    return public_user(u)


@app.post("/api/logout")
def logout(request: Request, response: Response):
    sid = request.cookies.get("sid")
    if sid:
        db.x("DELETE FROM sessions WHERE token=?", (sid,))
    response.delete_cookie("sid")
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    u = current_user(request)
    out = public_user(u)
    c = db.q("SELECT name FROM companies WHERE id=?", (u["company_id"],), one=True) if u["company_id"] else None
    out["company_name"] = c["name"] if c else None
    out["has_team"] = bool(subtree_ids(u["id"]))
    return out


@app.post("/api/me/password")
def change_pw(body: PwIn, request: Request):
    u = current_user(request)
    if not check_pw(body.current, u["password_hash"]):
        raise HTTPException(400, "Senha atual incorreta.")
    if len(body.new) < 8:
        raise HTTPException(400, "A nova senha precisa ter pelo menos 8 caracteres.")
    db.x("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body.new), u["id"]))
    return {"ok": True}


@app.get("/api/invite/{token}")
def invite_info(token: str):
    u = db.q("SELECT * FROM users WHERE invite_token=? AND active=1", (token,), one=True)
    if not u:
        raise HTTPException(404, "Convite inválido ou já utilizado.")
    c = db.q("SELECT name FROM companies WHERE id=?", (u["company_id"],), one=True)
    return {"name": u["name"], "email": u["email"], "company": c["name"] if c else None}


@app.post("/api/invite/{token}")
def invite_accept(token: str, body: InviteIn, response: Response):
    u = db.q("SELECT * FROM users WHERE invite_token=? AND active=1", (token,), one=True)
    if not u:
        raise HTTPException(404, "Convite inválido ou já utilizado.")
    if len(body.password) < 8:
        raise HTTPException(400, "A senha precisa ter pelo menos 8 caracteres.")
    db.x("UPDATE users SET password_hash=?, invite_token=NULL WHERE id=?", (hash_pw(body.password), u["id"]))
    return login(LoginIn(email=u["email"], password=body.password), response)


# ─── Questionário ─────────────────────────────────────────────────────────────

@app.get("/api/meta")
def meta(request: Request):
    current_user(request)
    profiles = {k: dict(p, key=list(p["key"])) for k, p in ins.PROFILES.items()}
    return {"bonds": ins.BONDS, "levels": ins.LEVELS, "profiles": profiles,
            "likert_labels": ins.LIKERT_LABELS, "presence_labels": ins.PRESENCE_LABELS,
            "roles": ROLE_LABEL, "min_group": MIN_GROUP,
            "cutoff": active_instrument()["data"].get("cutoffs", {}).get("high", 4.0)}


@app.get("/api/my/assignments")
def my_assignments(request: Request):
    u = current_user(request)
    return db.q("""SELECT a.id, a.status, a.completed_at, c.name AS campaign, c.deadline, c.status AS campaign_status
                   FROM assignments a JOIN campaigns c ON c.id=a.campaign_id
                   WHERE a.user_id=? ORDER BY a.id DESC""", (u["id"],))


@app.get("/api/assignments/{aid}")
def get_assignment(aid: int, request: Request):
    u = current_user(request)
    a = db.q("""SELECT a.*, c.instrument_id, c.name AS campaign, c.status AS campaign_status
                FROM assignments a JOIN campaigns c ON c.id=a.campaign_id WHERE a.id=?""", (aid,), one=True)
    if not a or a["user_id"] != u["id"]:
        raise HTTPException(404, "Questionário não encontrado.")
    data = instrument_by_id(a["instrument_id"])
    return {"id": a["id"], "status": a["status"], "campaign": a["campaign"], "campaign_status": a["campaign_status"],
            "instrument": {k: data[k] for k in ("title", "intro", "likert", "culture")}}


@app.post("/api/assignments/{aid}/submit")
def submit(aid: int, body: SubmitIn, request: Request):
    u = current_user(request)
    a = db.q("""SELECT a.*, c.instrument_id, c.status AS campaign_status
                FROM assignments a JOIN campaigns c ON c.id=a.campaign_id WHERE a.id=?""", (aid,), one=True)
    if not a or a["user_id"] != u["id"]:
        raise HTTPException(404, "Questionário não encontrado.")
    if a["status"] == "concluida":
        raise HTTPException(400, "Este questionário já foi respondido.")
    if a["campaign_status"] != "aberta":
        raise HTTPException(400, "Esta coleta já foi encerrada.")
    data = instrument_by_id(a["instrument_id"])
    for it in data["likert"]:
        v = body.likert.get(it["id"])
        if v is None or not 1 <= int(v) <= 6:
            raise HTTPException(400, "Responda todas as afirmativas.")
    for el in data["culture"]:
        r = body.rank.get(el["id"])
        if not r or sorted(r) != ["CN", "CO", "EN"]:
            raise HTTPException(400, f"Ordene as três frases do bloco {el['name']}.")
        p = body.presence.get(el["id"])
        if p is None or not 1 <= int(p) <= 4:
            raise HTTPException(400, f"Indique a força do elemento {el['name']}.")
    answers = body.dict()
    result = ins.score(data, answers)
    db.x("UPDATE assignments SET status='concluida', answers=?, result=?, completed_at=? WHERE id=?",
         (json.dumps(answers), json.dumps(result), datetime.utcnow().isoformat(timespec="seconds"), aid))
    return {"ok": True, "profile": result["profile"]}


# ─── Resultados e relatórios ──────────────────────────────────────────────────

@app.get("/api/results/{uid}")
def result_of(uid: int, request: Request, campaign_id: Optional[int] = None):
    v = current_user(request)
    if not can_view_user(v, uid):
        raise HTTPException(403, "Você não tem acesso ao resultado desta pessoa.")
    target = db.q("""SELECT u.*, a.name AS area, m.name AS manager FROM users u
                     LEFT JOIN areas a ON a.id=u.area_id LEFT JOIN users m ON m.id=u.manager_id
                     WHERE u.id=?""", (uid,), one=True)
    if not target:
        raise HTTPException(404, "Pessoa não encontrada.")
    res = results_for([uid], campaign_id).get(uid)
    history = db.q("""SELECT a.campaign_id, c.name, a.completed_at, a.result FROM assignments a
                      JOIN campaigns c ON c.id=a.campaign_id WHERE a.user_id=? AND a.status='concluida'
                      ORDER BY a.completed_at""", (uid,))
    hist = [{"campaign_id": h["campaign_id"], "campaign": h["name"], "completed_at": h["completed_at"],
             "bonds": json.loads(h["result"])["bonds"], "profile": json.loads(h["result"])["profile"]} for h in history]
    person = {"id": target["id"], "name": target["name"], "area": target["area"], "manager": target["manager"],
              "job_title": target["job_title"], "is_self": v["id"] == uid}
    if not res:
        return {"person": person, "result": None, "history": hist}
    r = res["result"]
    return {"person": person, "result": r, "completed_at": res["completed_at"], "campaign": res["campaign"],
            "profile": dict(ins.PROFILES[r["profile"]], key=list(ins.PROFILES[r["profile"]]["key"])),
            "reading": ins.culture_reading(r), "history": hist,
            "show_manager_tips": v["id"] != uid or ROLE_RANK[v["role"]] >= 1}


@app.get("/api/team")
def team(request: Request, company_id: Optional[int] = None, campaign_id: Optional[int] = None):
    v = current_user(request)
    if v["role"] == "master":
        cid = company_scope(v, company_id)
        ids = [r["id"] for r in db.q("SELECT id FROM users WHERE company_id=? AND active=1", (cid,))]
    else:
        ids = subtree_ids(v["id"])
    people = []
    if ids:
        ph = ",".join("?" * len(ids))
        people = db.q(f"""SELECT u.id, u.name, u.job_title, u.manager_id, u.area_id, a.name AS area, m.name AS manager
                         FROM users u LEFT JOIN areas a ON a.id=u.area_id LEFT JOIN users m ON m.id=u.manager_id
                         WHERE u.id IN ({ph}) AND u.active=1 ORDER BY u.name""", ids)
    res = results_for([p["id"] for p in people], campaign_id)
    for p in people:
        rr = res.get(p["id"])
        p["direct"] = p["manager_id"] == v["id"]
        if rr:
            r = rr["result"]
            p.update({"bonds": r["bonds"], "profile": r["profile"], "culture_share": r["culture_share"],
                      "levels": r["levels"], "completed_at": rr["completed_at"], "elements": r["elements"]})
    done = [res[p["id"]]["result"] for p in people if p["id"] in res]
    return {"people": people, "aggregate": aggregate(done)}


@app.get("/api/org")
def org(request: Request, company_id: Optional[int] = None, campaign_id: Optional[int] = None):
    v = require(request, "admin")
    cid = company_scope(v, company_id)
    company = db.q("SELECT * FROM companies WHERE id=?", (cid,), one=True)
    users = db.q("SELECT id, area_id FROM users WHERE company_id=? AND active=1 AND role!='master'", (cid,))
    res = results_for([u["id"] for u in users], campaign_id)
    areas = db.q("SELECT * FROM areas WHERE company_id=? ORDER BY name", (cid,))
    groups = []
    for a in areas + [{"id": None, "name": "Sem área"}]:
        members = [u["id"] for u in users if u["area_id"] == a["id"]]
        rs = [res[i]["result"] for i in members if i in res]
        if not members:
            continue
        g = {"id": a["id"], "name": a["name"], "members": len(members), "responded": len(rs)}
        if len(rs) >= MIN_GROUP or v["role"] == "master":
            g["aggregate"] = aggregate(rs)
        else:
            g["suppressed"] = True
        groups.append(g)
    allr = [r["result"] for r in res.values()]
    campaigns = db.q("SELECT id, name, status FROM campaigns WHERE company_id=? ORDER BY id DESC", (cid,))
    return {"company": company, "members": len(users), "responded": len(allr),
            "aggregate": aggregate(allr) if len(allr) >= MIN_GROUP or v["role"] == "master" else {"n": len(allr), "suppressed": True},
            "areas": groups, "campaigns": campaigns}


# ─── Administração: empresas, áreas e pessoas ─────────────────────────────────

@app.get("/api/companies")
def companies(request: Request):
    v = require(request, "admin")
    if v["role"] == "master":
        return db.q("""SELECT c.*, (SELECT count(*) FROM users u WHERE u.company_id=c.id) AS people
                       FROM companies c ORDER BY name""")
    return db.q("SELECT * FROM companies WHERE id=?", (v["company_id"],))


@app.post("/api/companies")
def company_create(body: CompanyIn, request: Request):
    require(request, "master")
    cid = db.x("INSERT INTO companies(name) VALUES(?)", (body.name.strip(),))
    return {"id": cid}


@app.delete("/api/companies/{cid}")
def company_delete(cid: int, request: Request):
    require(request, "master")
    db.x("DELETE FROM companies WHERE id=?", (cid,))
    return {"ok": True}


@app.get("/api/areas")
def areas(request: Request, company_id: Optional[int] = None):
    v = require(request, "gestor")
    cid = company_scope(v, company_id)
    return db.q("""SELECT a.*, (SELECT count(*) FROM users u WHERE u.area_id=a.id AND u.active=1) AS people
                   FROM areas a WHERE company_id=? ORDER BY name""", (cid,))


@app.post("/api/areas")
def area_create(body: AreaIn, request: Request):
    v = require(request, "admin")
    cid = company_scope(v, body.company_id)
    return {"id": db.x("INSERT INTO areas(company_id,name) VALUES(?,?)", (cid, body.name.strip()))}


@app.delete("/api/areas/{aid}")
def area_delete(aid: int, request: Request):
    v = require(request, "admin")
    a = db.q("SELECT * FROM areas WHERE id=?", (aid,), one=True)
    if not a or (v["role"] != "master" and a["company_id"] != v["company_id"]):
        raise HTTPException(404, "Área não encontrada.")
    db.x("DELETE FROM areas WHERE id=?", (aid,))
    return {"ok": True}


@app.get("/api/people")
def people(request: Request, company_id: Optional[int] = None):
    v = require(request, "admin")
    cid = company_scope(v, company_id)
    rows = db.q("""SELECT u.*, a.name AS area, m.name AS manager,
                   (SELECT count(*) FROM assignments x WHERE x.user_id=u.id AND x.status='concluida') AS answered
                   FROM users u LEFT JOIN areas a ON a.id=u.area_id LEFT JOIN users m ON m.id=u.manager_id
                   WHERE u.company_id=? ORDER BY u.name""", (cid,))
    out = []
    for r in rows:
        p = public_user(r)
        p.update({"area": r["area"], "manager": r["manager"], "answered": r["answered"]})
        if p["pending_invite"]:
            p["invite_link"] = invite_link(r)
        out.append(p)
    return out


def _check_role_assign(v: dict, role: str):
    if role not in ROLE_RANK:
        raise HTTPException(400, "Perfil de acesso inválido.")
    if role == "master" and v["role"] != "master":
        raise HTTPException(403, "Apenas o Master pode criar outro Master.")


@app.post("/api/people")
def person_create(body: PersonIn, request: Request):
    v = require(request, "admin")
    _check_role_assign(v, body.role)
    cid = company_scope(v, body.company_id)
    email = body.email.strip().lower()
    if db.q("SELECT id FROM users WHERE lower(email)=?", (email,), one=True):
        raise HTTPException(400, "Já existe uma pessoa com este e-mail.")
    tok = secrets.token_urlsafe(24)
    uid = db.x("""INSERT INTO users(company_id,area_id,manager_id,name,email,job_title,role,invite_token)
                  VALUES(?,?,?,?,?,?,?,?)""",
               (cid, body.area_id, body.manager_id, body.name.strip(), email, body.job_title, body.role, tok))
    return {"id": uid, "invite_link": f"{APP_BASE_URL}/#/convite/{tok}"}


@app.put("/api/people/{uid}")
def person_update(uid: int, body: PersonIn, request: Request):
    v = require(request, "admin")
    t = db.q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not t or not manageable(v, t):
        raise HTTPException(404, "Pessoa não encontrada.")
    _check_role_assign(v, body.role)
    if body.manager_id == uid or (body.manager_id and body.manager_id in subtree_ids(uid)):
        raise HTTPException(400, "Uma pessoa não pode ser gestora de quem está acima dela.")
    if uid == v["id"] and body.role != v["role"]:
        raise HTTPException(400, "Você não pode alterar o seu próprio perfil de acesso.")
    db.x("""UPDATE users SET name=?, email=?, job_title=?, role=?, area_id=?, manager_id=?, active=? WHERE id=?""",
         (body.name.strip(), body.email.strip().lower(), body.job_title, body.role, body.area_id,
          body.manager_id, 1 if body.active else 0, uid))
    return {"ok": True}


@app.delete("/api/people/{uid}")
def person_delete(uid: int, request: Request):
    v = require(request, "admin")
    t = db.q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not t or not manageable(v, t) or uid == v["id"]:
        raise HTTPException(404, "Pessoa não encontrada.")
    db.x("DELETE FROM users WHERE id=?", (uid,))
    return {"ok": True}


@app.post("/api/people/{uid}/invite")
def person_invite(uid: int, request: Request):
    v = require(request, "admin")
    t = db.q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not t or not manageable(v, t):
        raise HTTPException(404, "Pessoa não encontrada.")
    tok = secrets.token_urlsafe(24)
    # Reenviar convite também serve para redefinir a senha
    db.x("UPDATE users SET invite_token=?, password_hash=NULL WHERE id=?", (tok, uid))
    db.x("DELETE FROM sessions WHERE user_id=?", (uid,))
    link = f"{APP_BASE_URL}/#/convite/{tok}"
    sent = send_mail(t["email"], "Seu acesso ao Diagnóstico de Vínculos",
                     f"Olá, {t['name']}!\n\nVocê foi convidado(a) para o Diagnóstico de Vínculos e Cultura.\n"
                     f"Crie sua senha neste link: {link}\n\nUngari Mentoria & Consultoria")
    return {"invite_link": link, "email_sent": sent}


# ─── Campanhas (disparo de formulários) ───────────────────────────────────────

@app.get("/api/campaigns")
def campaigns(request: Request, company_id: Optional[int] = None):
    v = require(request, "admin")
    cid = company_scope(v, company_id)
    return db.q("""SELECT c.*, (SELECT count(*) FROM assignments a WHERE a.campaign_id=c.id) AS total,
                   (SELECT count(*) FROM assignments a WHERE a.campaign_id=c.id AND a.status='concluida') AS done
                   FROM campaigns c WHERE company_id=? ORDER BY id DESC""", (cid,))


@app.post("/api/campaigns")
def campaign_create(body: CampaignIn, request: Request):
    v = require(request, "admin")
    cid = company_scope(v, body.company_id)
    if body.user_ids:
        ph = ",".join("?" * len(body.user_ids))
        targets = db.q(f"SELECT * FROM users WHERE company_id=? AND active=1 AND id IN ({ph})", [cid] + body.user_ids)
    elif body.area_ids:
        ph = ",".join("?" * len(body.area_ids))
        targets = db.q(f"SELECT * FROM users WHERE company_id=? AND active=1 AND area_id IN ({ph})", [cid] + body.area_ids)
    else:
        targets = db.q("SELECT * FROM users WHERE company_id=? AND active=1 AND role!='master'", (cid,))
    if not targets:
        raise HTTPException(400, "Nenhuma pessoa selecionada.")
    inst = active_instrument()
    camp = db.x("INSERT INTO campaigns(company_id,name,instrument_id,deadline,created_by) VALUES(?,?,?,?,?)",
                (cid, body.name.strip(), inst["id"], body.deadline, v["id"]))
    links, sent = [], 0
    for t in targets:
        db.x("INSERT OR IGNORE INTO assignments(campaign_id,user_id) VALUES(?,?)", (camp, t["id"]))
        if t["invite_token"] and not t["password_hash"]:
            link = invite_link(t)
        else:
            link = f"{APP_BASE_URL}/#/inicio"
        prazo = f" até {body.deadline}" if body.deadline else ""
        ok = send_mail(t["email"], f"Diagnóstico de Vínculos: {body.name}",
                       f"Olá, {t['name']}!\n\nVocê tem um questionário para responder{prazo}. "
                       f"Leva cerca de 7 minutos.\nAcesse: {link}\n\nUngari Mentoria & Consultoria")
        sent += 1 if ok else 0
        links.append({"name": t["name"], "email": t["email"], "link": link})
    return {"id": camp, "count": len(targets), "emails_sent": sent, "links": links}


@app.get("/api/campaigns/{cid}")
def campaign_detail(cid: int, request: Request):
    v = require(request, "admin")
    c = db.q("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)
    if not c or (v["role"] != "master" and c["company_id"] != v["company_id"]):
        raise HTTPException(404, "Coleta não encontrada.")
    rows = db.q("""SELECT a.id, a.status, a.completed_at, u.id AS user_id, u.name, u.email, u.invite_token,
                   u.password_hash, ar.name AS area
                   FROM assignments a JOIN users u ON u.id=a.user_id LEFT JOIN areas ar ON ar.id=u.area_id
                   WHERE a.campaign_id=? ORDER BY u.name""", (cid,))
    for r in rows:
        r["link"] = invite_link(r) if r["invite_token"] and not r["password_hash"] else f"{APP_BASE_URL}/#/inicio"
        r.pop("password_hash", None)
        r.pop("invite_token", None)
    return {"campaign": c, "assignments": rows}


@app.post("/api/campaigns/{cid}/status")
def campaign_status(cid: int, request: Request, status: str = "encerrada"):
    v = require(request, "admin")
    c = db.q("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)
    if not c or (v["role"] != "master" and c["company_id"] != v["company_id"]) or status not in ("aberta", "encerrada"):
        raise HTTPException(404, "Coleta não encontrada.")
    db.x("UPDATE campaigns SET status=? WHERE id=?", (status, cid))
    return {"ok": True}


@app.delete("/api/campaigns/{cid}")
def campaign_delete(cid: int, request: Request):
    require(request, "master")
    db.x("DELETE FROM campaigns WHERE id=?", (cid,))
    return {"ok": True}


# ─── Instrumento (Master) ─────────────────────────────────────────────────────

@app.get("/api/instrument")
def instrument_get(request: Request):
    require(request, "master")
    inst = active_instrument()
    versions = db.q("SELECT id, note, created_at, active FROM instruments ORDER BY id DESC")
    return {"active": inst, "versions": versions, "default": ins.default_instrument()}


@app.put("/api/instrument")
def instrument_put(body: InstrumentIn, request: Request):
    v = require(request, "master")
    validate_instrument(body.data)
    db.x("UPDATE instruments SET active=0")
    iid = db.x("INSERT INTO instruments(data,note,created_by,active) VALUES(?,?,?,1)",
               (json.dumps(body.data, ensure_ascii=False), body.note, v["id"]))
    return {"id": iid}


# ─── Inicialização ────────────────────────────────────────────────────────────

def bootstrap():
    db.init()
    if not db.q("SELECT id FROM instruments LIMIT 1"):
        db.x("INSERT INTO instruments(data,note,active) VALUES(?,?,1)",
             (json.dumps(ins.default_instrument(), ensure_ascii=False), "Versão inicial (IUVC v1)"))
    if not db.q("SELECT id FROM users WHERE role='master' LIMIT 1"):
        email = os.environ.get("MASTER_EMAIL", "diegoungari04@gmail.com")
        if APP_BASE_URL.startswith("https") and not os.environ.get("MASTER_PASSWORD"):
            # Em produção: o Master cria a própria senha por um link de primeiro acesso, impresso no log
            tok = secrets.token_urlsafe(24)
            db.x("INSERT INTO users(name,email,role,invite_token) VALUES(?,?,?,?)",
                 ("Diego Ungari", email, "master", tok))
            print(f"[ungari-vinculos] Primeiro acesso Master: {APP_BASE_URL}/#/convite/{tok}", flush=True)
            return
        pw = os.environ.get("MASTER_PASSWORD") or secrets.token_urlsafe(10)
        db.x("INSERT INTO users(name,email,role,password_hash) VALUES(?,?,?,?)",
             ("Diego Ungari", email, "master", hash_pw(pw)))
        if not os.environ.get("MASTER_PASSWORD"):
            f = Path(db.DB_PATH).parent / "CREDENCIAIS_INICIAIS.txt"
            f.write_text(f"Acesso Master inicial\nE-mail: {email}\nSenha: {pw}\n"
                         "Troque a senha no primeiro acesso (menu Minha conta) e apague este arquivo.\n")


bootstrap()


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
