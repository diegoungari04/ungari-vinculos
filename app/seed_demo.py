"""
Cria uma empresa de demonstração com áreas, gestores, colaboradores e respostas simuladas.
Uso:  ./venv/bin/python -m app.seed_demo
Remover: excluir a empresa "Empresa Demonstração" pela tela Empresas (Master).
"""
import json
import random
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from . import db
from . import instrument as ins
from .main import hash_pw, active_instrument

random.seed(7)

# Perfil-alvo -> médias aproximadas (CO, CN, EN) na escala 1 a 6
ARCH = {
    "PROTAGONISTA": (5.3, 2.6, 2.4), "GUARDIAO": (5.0, 4.9, 2.8), "ENRAIZADO": (4.8, 2.9, 4.7),
    "ANCORA": (5.0, 4.8, 4.8), "CUMPRIDOR": (3.0, 4.9, 2.7), "RESIGNADO": (2.6, 4.7, 5.0),
    "NA_TRINCHEIRA": (2.7, 2.8, 5.1), "EM_TRANSITO": (2.8, 2.6, 2.5),
}

AREAS = {
    "Operações": ["GUARDIAO", "GUARDIAO", "ANCORA", "CUMPRIDOR", "RESIGNADO", "GUARDIAO"],
    "Comercial": ["PROTAGONISTA", "PROTAGONISTA", "EM_TRANSITO", "NA_TRINCHEIRA", "PROTAGONISTA"],
    "Tecnologia": ["PROTAGONISTA", "EM_TRANSITO", "ENRAIZADO", "EM_TRANSITO", "PROTAGONISTA"],
    "Administrativo": ["RESIGNADO", "NA_TRINCHEIRA", "CUMPRIDOR", "ENRAIZADO"],
}
NAMES = ["Ana Souza", "Bruno Lima", "Carla Mendes", "Daniel Rocha", "Elisa Prado", "Felipe Araújo",
         "Gabriela Nunes", "Heitor Campos", "Isabela Reis", "João Pires", "Karina Lopes", "Lucas Martins",
         "Marina Teixeira", "Nicolas Duarte", "Olívia Barros", "Paulo Moreira", "Renata Farias",
         "Sérgio Castro", "Tatiana Gomes", "Vitor Azevedo"]
MANAGERS = {"Operações": ("Roberta Vieira", "ANCORA"), "Comercial": ("Marcelo Tavares", "PROTAGONISTA"),
            "Tecnologia": ("Juliana Ramos", "ENRAIZADO"), "Administrativo": ("Fernando Costa", "GUARDIAO")}


def clamp(v):
    return max(1, min(6, int(round(v))))


def simulate(inst, arch):
    target = dict(zip(("CO", "CN", "EN"), ARCH[arch]))
    likert = {}
    for it in inst["likert"]:
        v = clamp(random.gauss(target[it["bond"]], 0.6))
        likert[it["id"]] = 7 - v if it.get("reverse") else v
    rank, presence = {}, {}
    for el in inst["culture"]:
        w = {b: target[b] + random.gauss(0, 0.9) for b in ("CO", "CN", "EN")}
        if el["level"] == "VAL" and el["id"] == "NORMAS":
            w["CN"] += 0.6
        rank[el["id"]] = sorted(w, key=w.get, reverse=True)
        presence[el["id"]] = max(1, min(4, int(round(random.gauss(2.8 if target["CO"] > 4 else 2.2, 0.8)))))
    return {"likert": likert, "rank": rank, "presence": presence}


def main():
    if db.q("SELECT id FROM companies WHERE name='Empresa Demonstração'", one=True):
        print("Empresa Demonstração já existe.")
        return
    pw = secrets.token_urlsafe(8)
    h = hash_pw(pw)
    inst_row = active_instrument()
    inst = inst_row["data"]
    cid = db.x("INSERT INTO companies(name) VALUES('Empresa Demonstração')")
    admin = db.x("INSERT INTO users(company_id,name,email,job_title,role,password_hash) VALUES(?,?,?,?,?,?)",
                 (cid, "Patrícia Alves", "admin@demo.ungari", "Business Partner de RH", "admin", h))
    diretor = db.x("INSERT INTO users(company_id,name,email,job_title,role,password_hash) VALUES(?,?,?,?,?,?)",
                   (cid, "Ricardo Menezes", "diretor@demo.ungari", "Diretor Geral", "gestor", h))
    camp_old = db.x("INSERT INTO campaigns(company_id,name,instrument_id,status) VALUES(?,?,?,?)",
                    (cid, "Ciclo 2026.1", inst_row["id"], "encerrada"))
    camp = db.x("INSERT INTO campaigns(company_id,name,instrument_id,status,deadline) VALUES(?,?,?,?,?)",
                (cid, "Ciclo 2026.2", inst_row["id"], "aberta", "2026-11-30"))
    names = iter(NAMES)
    people = []
    for area, archs in AREAS.items():
        aid = db.x("INSERT INTO areas(company_id,name) VALUES(?,?)", (cid, area))
        mname, march = MANAGERS[area]
        slug = mname.split()[0].lower()
        mid = db.x("""INSERT INTO users(company_id,area_id,manager_id,name,email,job_title,role,password_hash)
                      VALUES(?,?,?,?,?,?,?,?)""",
                   (cid, aid, diretor, mname, f"{slug}@demo.ungari", f"Gerente de {area}", "gestor", h))
        people.append((mid, march))
        for i, arch in enumerate(archs):
            n = next(names)
            slug = n.split()[0].lower()
            uid = db.x("""INSERT INTO users(company_id,area_id,manager_id,name,email,job_title,role,password_hash)
                          VALUES(?,?,?,?,?,?,?,?)""",
                       (cid, aid, mid, n, f"{slug}@demo.ungari", "Analista", "colaborador", h))
            people.append((uid, arch))
    now = datetime.utcnow()
    for k, (uid, arch) in enumerate(people):
        # ciclo anterior: perfil levemente diferente para mostrar evolução
        old_arch = arch if k % 3 else random.choice(list(ARCH))
        ans = simulate(inst, old_arch)
        db.x("INSERT INTO assignments(campaign_id,user_id,status,answers,result,completed_at) VALUES(?,?,?,?,?,?)",
             (camp_old, uid, "concluida", json.dumps(ans), json.dumps(ins.score(inst, ans)),
              (now - timedelta(days=180)).isoformat(timespec="seconds")))
        if k % 7 == 6:  # alguns ainda não responderam o ciclo atual
            db.x("INSERT INTO assignments(campaign_id,user_id) VALUES(?,?)", (camp, uid))
            continue
        ans = simulate(inst, arch)
        db.x("INSERT INTO assignments(campaign_id,user_id,status,answers,result,completed_at) VALUES(?,?,?,?,?,?)",
             (camp, uid, "concluida", json.dumps(ans), json.dumps(ins.score(inst, ans)),
              (now - timedelta(days=random.randint(1, 10))).isoformat(timespec="seconds")))
    db.x("INSERT INTO assignments(campaign_id,user_id) VALUES(?,?)", (camp, admin))
    f = Path(db.DB_PATH).parent / "CREDENCIAIS_INICIAIS.txt"
    with open(f, "a") as fh:
        fh.write(f"\nEmpresa Demonstração (dados fictícios)\nSenha de todas as contas demo: {pw}\n"
                 "Admin: admin@demo.ungari | Diretor (gestor de gestores): diretor@demo.ungari\n"
                 "Gestora Operações: roberta@demo.ungari | Colaboradora: ana@demo.ungari\n")
    print("Demo criada. Credenciais em", f)


if __name__ == "__main__":
    main()
