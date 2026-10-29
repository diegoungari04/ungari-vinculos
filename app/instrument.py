"""
Instrumento Ungari de Vínculos e Cultura (IUVC).

Base teórica:
- Vínculos: Comprometimento (Bastos & Aguiar, 2015; Meyer & Allen, 1991; Mowday et al., 1982),
  Consentimento (Silva, 2009, 2013; Silva & Bastos, 2015) e Entrincheiramento
  (Rodrigues, 2009; Rodrigues & Bastos, 2012, 2015).
- Cultura: elementos de Freitas (2007) + Espírito de Corpo (Ungari, 2019),
  agrupados nos três níveis de Schein (2009): Artefatos, Valores e Normas, Pressupostos.
- Relação cultura x vínculo: Quadro 10 da dissertação de Ungari (2019).

Parte 1 (12 itens Likert 1-6) mede a força absoluta de cada vínculo.
Parte 2 (8 blocos de ordenação + presença 1-4) mede por qual vínculo cada elemento
da cultura chega até a pessoa, e o quanto esse elemento é forte para ela.
"""
import copy

BONDS = {
    "CO": {"name": "Comprometimento", "short": "Querer ficar",
           "desc": "Ligação afetiva: orgulho, pertencimento e identificação com a organização."},
    "CN": {"name": "Consentimento", "short": "Dever obedecer",
           "desc": "Ligação pela obediência: cumprir o que é determinado porque a autoridade é de quem manda."},
    "EN": {"name": "Entrincheiramento", "short": "Precisar ficar",
           "desc": "Ligação pela necessidade: ficar pelo que se perderia ao sair ou pela falta de alternativas."},
}

LEVELS = {
    "ART": {"name": "Artefatos", "desc": "O que se vê e se vive: ritos, cerimônias, histórias e figuras de referência."},
    "VAL": {"name": "Valores e Normas", "desc": "O que a organização diz que é importante e como espera que se faça."},
    "PRE": {"name": "Pressupostos", "desc": "As verdades que ninguém questiona e os assuntos que ninguém toca."},
}

LIKERT_LABELS = ["Discordo totalmente", "Discordo", "Discordo em parte",
                 "Concordo em parte", "Concordo", "Concordo totalmente"]
PRESENCE_LABELS = ["Quase ausente", "Presente", "Forte", "Muito forte"]

DEFAULT_INSTRUMENT = {
    "title": "Diagnóstico de Vínculos e Cultura",
    "intro": ("Não existem respostas certas ou erradas. O objetivo é entender como você se liga "
              "à organização e como a cultura daqui chega até você. Responda pensando no seu dia a dia "
              "atual. Leva cerca de 7 minutos."),
    "cutoffs": {"high": 4.0, "border": 0.35},
    "likert": [
        {"id": "CO1", "bond": "CO", "sub": "Orgulho", "reverse": False,
         "text": "Sinto orgulho de dizer às pessoas que faço parte desta organização."},
        {"id": "CN1", "bond": "CN", "sub": "Obediência", "reverse": False,
         "text": "Os superiores têm a autoridade. Cabe a mim cumprir o que é determinado."},
        {"id": "EN1", "bond": "EN", "sub": "Ajustamento à posição social", "reverse": False,
         "text": "Se eu saísse daqui, sentiria que joguei fora todo o esforço que fiz para chegar onde estou."},
        {"id": "CO2", "bond": "CO", "sub": "Pertencimento", "reverse": False,
         "text": "Esta organização tem um significado pessoal muito grande para mim."},
        {"id": "CN2", "bond": "CN", "sub": "Obediência", "reverse": False,
         "text": "Mesmo quando algo me incomoda no trabalho, faço o que foi determinado."},
        {"id": "EN2", "bond": "EN", "sub": "Arranjos burocráticos impessoais", "reverse": False,
         "text": "Sair desta organização agora colocaria em risco a minha estabilidade financeira."},
        {"id": "CO3", "bond": "CO", "sub": "Identificação", "reverse": False,
         "text": "Sinto os objetivos desta organização como se fossem meus."},
        {"id": "CN3", "bond": "CN", "sub": "Obediência", "reverse": False,
         "text": "Quando recebo uma determinação, a responsabilidade pelo resultado é de quem a deu."},
        {"id": "EN3", "bond": "EN", "sub": "Arranjos burocráticos impessoais", "reverse": False,
         "text": "Eu perderia benefícios difíceis de encontrar em outro lugar se saísse daqui."},
        {"id": "CO4", "bond": "CO", "sub": "Identificação", "reverse": False,
         "text": "Meus valores são muito parecidos com os valores que esta organização defende."},
        {"id": "CN4", "bond": "CN", "sub": "Obediência", "reverse": True,
         "text": "Quando não concordo com uma orientação da liderança, questiono antes de cumprir."},
        {"id": "EN4", "bond": "EN", "sub": "Limitação de alternativas", "reverse": False,
         "text": "Continuo aqui porque sinto que tenho poucas oportunidades em outras organizações."},
    ],
    "culture": [
        {"id": "VALORES", "level": "VAL", "name": "Valores",
         "prompt": "Os valores da organização, aquilo que ela diz ser importante...",
         "options": {
             "CO": "Já tinham a ver comigo antes de eu chegar. Eu me reconheço neles.",
             "CN": "Fui aprendendo a segui-los aqui dentro, porque é o que se espera de mim.",
             "EN": "Não são o que me mantém aqui. Fico pelo que eu perderia se saísse."}},
        {"id": "NORMAS", "level": "VAL", "name": "Normas e regras",
         "prompt": "As normas, regras e a hierarquia daqui...",
         "options": {
             "CO": "Entendo para que servem e sigo porque concordo com elas.",
             "CN": "Sigo porque é a regra e quem decide é a liderança, mesmo quando não concordo.",
             "EN": "Me amarram, mas aprendi a funcionar nesse sistema e recomeçar em outro lugar seria difícil."}},
        {"id": "ESPIRITO", "level": "VAL", "name": "Espírito de corpo",
         "prompt": "A união do grupo, o sentimento de equipe...",
         "options": {
             "CO": "Me faz sentir parte de algo maior. É um dos motivos de eu gostar daqui.",
             "CN": "Significa acompanhar o que o grupo faz, sem destoar.",
             "EN": "Meus laços aqui seriam difíceis de reconstruir e isso pesa na decisão de ficar."}},
        {"id": "RITOS", "level": "ART", "name": "Ritos, rituais e cerimônias",
         "prompt": "Os eventos, celebrações, integrações e momentos de reconhecimento...",
         "options": {
             "CO": "Aumentam meu orgulho e meu sentimento de pertencer.",
             "CN": "Servem para lembrar como devemos nos comportar e a quem devemos responder.",
             "EN": "Participo porque faz parte. O que conta para mim é o que já conquistei aqui."}},
        {"id": "HISTORIAS", "level": "ART", "name": "Histórias",
         "prompt": "As histórias que se contam sobre o passado da organização...",
         "options": {
             "CO": "Me emocionam e reforçam minha ligação com a organização.",
             "CN": "Mostram o que acontece com quem segue, ou não segue, o padrão.",
             "EN": "Falam de quem ficou porque mudar era arriscado demais. Me reconheço nisso."}},
        {"id": "HEROIS", "level": "ART", "name": "Sagas e heróis",
         "prompt": "As lideranças e figuras de referência daqui...",
         "options": {
             "CO": "Me inspiram a dar o meu melhor. Admiro a trajetória delas.",
             "CN": "São exemplos de disciplina e de respeito à hierarquia que procuro seguir.",
             "EN": "Mostram um caminho longo que já comecei a percorrer. Desistir agora seria desperdício."}},
        {"id": "CRENCAS", "level": "PRE", "name": "Crenças e pressupostos",
         "prompt": "As \"verdades\" da organização, aquilo que ninguém costuma questionar...",
         "options": {
             "CO": "Acredito nelas de verdade. Fazem sentido para mim.",
             "CN": "Tenho minhas críticas, mas não cabe a mim questioná-las.",
             "EN": "Tenho críticas, mas acho que em qualquer lugar seria igual ou pior, então fico."}},
        {"id": "TABUS", "level": "PRE", "name": "Tabus",
         "prompt": "Os assuntos difíceis, os erros e aquilo que \"não se fala\" por aqui...",
         "options": {
             "CO": "Quando algo dá errado, conseguimos conversar e aprender juntos.",
             "CN": "Há assuntos que é melhor não tocar. Prefiro seguir sem levantar questões.",
             "EN": "Há coisas que me incomodam e me prendem, mas não vejo saída."}},
    ],
}


def default_instrument():
    return copy.deepcopy(DEFAULT_INSTRUMENT)


# ─── Perfis (clusters) ─────────────────────────────────────────────────────────
# Chave: (CO alto?, CN alto?, EN alto?)

PROFILES = {
    "PROTAGONISTA": {
        "key": (1, 0, 0), "name": "Protagonista", "color": "#2D7A5A",
        "tagline": "Fica porque quer e pensa com a própria cabeça.",
        "summary": ("Seu vínculo com a organização é sustentado principalmente pelo afeto: orgulho, "
                    "pertencimento e identificação com o que a organização é e defende. Você não se sente "
                    "preso(a) por necessidade e também não se liga pela obediência. Quando concorda, se "
                    "entrega. Quando discorda, questiona. Na literatura, esse é o padrão mais associado a "
                    "comportamentos que vão além do prescrito: iniciativa, cooperação espontânea e cuidado "
                    "genuíno com os resultados."),
        "strengths": ["Engajamento espontâneo, que não depende de controle", "Postura crítica e construtiva diante das regras",
                      "Disposição para propor melhorias e assumir responsabilidade", "Liberdade real de escolha: está aqui por decisão"],
        "risks": ["Se os valores da organização mudarem ou forem traídos, o vínculo pode romper rápido",
                  "Pode se frustrar em ambientes muito hierárquicos que não abrem espaço para ideias",
                  "Tende a assumir demais e se sobrecarregar pelo senso de dono"],
        "next_steps": ["Mapeie quais valores da organização mais se conectam com os seus e onde estão as tensões",
                       "Transforme suas críticas em propostas concretas, levadas aos fóruns certos",
                       "Combine com sua liderança um desafio que amplie seu escopo de influência",
                       "Cuide dos limites: comprometimento não é disponibilidade infinita"],
        "manager": ["Dê autonomia real e desafios com significado. Controle excessivo corrói esse vínculo",
                    "Explique o porquê das decisões. Essa pessoa adere a razões, não a ordens",
                    "Abra espaço formal para ideias e devolutivas sobre o que foi feito com elas",
                    "Observe sinais de sobrecarga e ajude a priorizar",
                    "Seja coerente com os valores declarados. Incoerência é o maior risco de perda"],
    },
    "GUARDIAO": {
        "key": (1, 1, 0), "name": "Guardião", "color": "#1D4E3A",
        "tagline": "Veste a camisa e respeita a hierarquia.",
        "summary": ("Você combina um vínculo afetivo forte com um forte senso de dever diante da autoridade. "
                    "Gosta de estar aqui, sente orgulho e, ao mesmo tempo, entende que seguir a hierarquia e as "
                    "regras é parte do que significa pertencer. Na pesquisa com a Polícia Militar de Santa "
                    "Catarina, esse foi o padrão mais frequente: culturas com rituais fortes, normas claras e "
                    "hierarquia valorizada tendem a formar Guardiões. O ponto de atenção é que a obediência pode "
                    "silenciar o seu olhar crítico."),
        "strengths": ["Lealdade e confiabilidade elevadas", "Alto alinhamento com a cultura e com a liderança",
                      "Estabilidade emocional do time em momentos de crise", "Senso de missão e de dever"],
        "risks": ["Executar sem questionar, mesmo quando algo parece errado",
                  "Pouca iniciativa para mudar o que \"sempre foi assim\"",
                  "Dificuldade de lidar com lideranças que pedem autonomia ou com mudanças culturais"],
        "next_steps": ["Pratique trazer pelo menos uma pergunta ou sugestão por semana para sua liderança",
                       "Diferencie respeito à hierarquia de concordância automática",
                       "Busque entender o porquê das regras que você segue",
                       "Experimente liderar uma pequena melhoria de processo do início ao fim"],
        "manager": ["Convide explicitamente para opinar. Essa pessoa espera permissão para discordar",
                    "Reconheça publicamente a lealdade, mas premie também a iniciativa",
                    "Delegue decisões, não só tarefas, e aumente a autonomia aos poucos",
                    "Em mudanças, explique o que permanece e o que muda. A estabilidade importa para esse perfil",
                    "Cuidado para não usar a disposição em obedecer como atalho de gestão"],
    },
    "ENRAIZADO": {
        "key": (1, 0, 1), "name": "Enraizado", "color": "#3F6B4F",
        "tagline": "Ama o lugar e também tem muito em jogo aqui.",
        "summary": ("Você sente uma ligação afetiva verdadeira com a organização e, ao mesmo tempo, percebe que "
                    "sair teria um custo alto: investimentos de carreira, estabilidade financeira ou poucas "
                    "alternativas. Você não se liga pela obediência, então mantém seu senso crítico. É um vínculo "
                    "sólido, mas com raízes de duas naturezas: o querer e o precisar. O desafio é garantir que o "
                    "querer continue sendo o motivo principal."),
        "strengths": ["Vínculo estável e de longo prazo", "Conhecimento profundo da organização",
                      "Senso crítico preservado", "Disposição para investir no futuro da organização"],
        "risks": ["Se o afeto diminuir, o que sobra é a sensação de estar preso(a)",
                  "Pode adiar decisões de carreira importantes por segurança",
                  "Acomodação em uma zona de conforto confortável demais"],
        "next_steps": ["Separe o que você ama aqui do que você teme perder. Escreva as duas listas",
                       "Invista em empregabilidade: aprendizados e redes que valham dentro e fora daqui",
                       "Converse sobre seu plano de carreira com a liderança",
                       "Reavalie a cada ciclo se você continuaria aqui sem os custos de sair"],
        "manager": ["Reforce o lado afetivo: propósito, reconhecimento e participação em decisões",
                    "Ofereça desenvolvimento que aumente a autonomia de carreira. Isso fortalece o querer ficar",
                    "Converse abertamente sobre perspectivas, sem usar a dependência como retenção",
                    "Esteja atento(a) a sinais de desânimo, que podem indicar migração para o perfil Na Trincheira"],
    },
    "ANCORA": {
        "key": (1, 1, 1), "name": "Âncora", "color": "#24533F",
        "tagline": "Ligado(a) por todos os motivos possíveis.",
        "summary": ("Os três vínculos aparecem fortes em você: você gosta da organização, sente o dever de "
                    "seguir a autoridade e também percebe que sair teria um custo alto. É o padrão mais intenso de "
                    "ligação. Para a organização, representa grande permanência. Para você, vale olhar se essa "
                    "ancoragem está te sustentando ou te imobilizando, porque quando todos os laços apertam ao "
                    "mesmo tempo, fica difícil saber qual deles realmente escolheu ficar."),
        "strengths": ["Altíssima permanência e lealdade", "Referência de cultura para os demais",
                      "Disposição para cumprir e para se dedicar"],
        "risks": ["Dificuldade em diferenciar desejo, dever e necessidade",
                  "Risco de sobrecarga e de dizer sim a tudo",
                  "Baixa abertura para mudanças, dentro e fora da organização"],
        "next_steps": ["Pergunte-se: se nada me prendesse, eu escolheria estar aqui? Por quê?",
                       "Identifique quais regras você segue por convicção e quais por hábito",
                       "Crie alternativas reais para você, mesmo que não pretenda usá-las",
                       "Pratique dizer não em situações de baixo risco"],
        "manager": ["Valorize a dedicação sem explorá-la. Esse perfil raramente reclama",
                    "Ajude a pessoa a encontrar sentido e não só obrigação nas tarefas",
                    "Estimule autonomia e opinião própria, com segurança psicológica",
                    "Acompanhe sinais de esgotamento"],
    },
    "CUMPRIDOR": {
        "key": (0, 1, 0), "name": "Cumpridor", "color": "#5C6B63",
        "tagline": "Faz o que precisa ser feito, do jeito que foi pedido.",
        "summary": ("Seu vínculo é baseado principalmente na obediência. Você cumpre as determinações porque "
                    "reconhece a autoridade de quem decide, mas sem uma ligação afetiva forte e sem se sentir "
                    "preso(a) por necessidade. Silva (2013) mostra que esse padrão tende a manter as pessoas "
                    "dentro do trabalho prescrito: entrega o combinado, mas raramente vai além. Muitas vezes, é "
                    "um sinal de que a cultura ainda não encontrou um jeito de se conectar com você."),
        "strengths": ["Disciplina e previsibilidade", "Respeito a processos e regras",
                      "Facilidade de adaptação a estruturas claras"],
        "risks": ["Pouco envolvimento afetivo e baixa iniciativa",
                  "Insatisfação silenciosa, que não aparece até virar saída",
                  "Transferência de responsabilidade para a liderança"],
        "next_steps": ["Identifique o que no seu trabalho te dá energia e o que só te ocupa",
                       "Procure uma causa ou projeto da organização com o qual você se identifique",
                       "Experimente dar sua opinião antes de executar uma tarefa importante",
                       "Converse com sua liderança sobre o que te faria gostar mais daqui"],
        "manager": ["Pergunte o que a pessoa pensa. O silêncio não é concordância",
                    "Conecte as tarefas ao propósito e ao impacto que elas geram",
                    "Crie pequenas oportunidades de autonomia e reconheça quando ela é usada",
                    "Investigue se há insatisfações não ditas, em conversas individuais e seguras",
                    "Evite gerir apenas por comando: isso reforça o padrão"],
    },
    "RESIGNADO": {
        "key": (0, 1, 1), "name": "Resignado", "color": "#8A6A3B",
        "tagline": "Obedece e fica, mas o coração está longe.",
        "summary": ("Você se mantém na organização pela combinação de obediência e necessidade: cumpre o que é "
                    "determinado e sente que sair teria um custo alto ou que há poucas alternativas, mas sem uma "
                    "ligação afetiva forte. Pinho, Bastos e Rowe (2015) associam esses vínculos à submissão, à "
                    "insatisfação e à acomodação. Não é um rótulo sobre quem você é, mas um retrato de um momento "
                    "que merece cuidado e que pode ser transformado."),
        "strengths": ["Constância e cumprimento das obrigações", "Conhecimento acumulado da rotina",
                      "Resiliência diante de contextos difíceis"],
        "risks": ["Desgaste emocional e queda de bem-estar", "Sensação de não ter voz nem saída",
                  "Desengajamento progressivo"],
        "next_steps": ["Reconheça o que te prende e o que te afasta. Nomear ajuda a decidir",
                       "Invista em pelo menos uma competência que amplie suas alternativas",
                       "Busque apoio: liderança, RH, mentoria ou rede de confiança",
                       "Encontre algo, mesmo pequeno, no trabalho que tenha significado para você"],
        "manager": ["Priorize uma conversa individual de escuta, sem julgamento",
                    "Investigue o que gerou esse distanciamento: liderança, carga, reconhecimento, injustiças",
                    "Ofereça desenvolvimento como sinal de investimento genuíno na pessoa",
                    "Dê voz em decisões que afetam o trabalho dela",
                    "Se não houver caminho de reconexão, apoie uma transição respeitosa"],
    },
    "NA_TRINCHEIRA": {
        "key": (0, 0, 1), "name": "Na Trincheira", "color": "#A0522D",
        "tagline": "Fica porque sair parece arriscado demais.",
        "summary": ("Seu principal vínculo é o entrincheiramento: você permanece porque sair significaria perder "
                    "investimentos, estabilidade ou benefícios, ou porque vê poucas alternativas. Assim como o "
                    "soldado na trincheira, a posição protege, mas também imobiliza. Rodrigues (2009) descreve "
                    "esse vínculo como busca de proteção, segurança e manutenção do status quo. É um sinal "
                    "importante para olhar sua carreira com mais intenção."),
        "strengths": ["Senso de responsabilidade com a própria segurança e com a família",
                      "Conhecimento técnico acumulado", "Pensamento crítico preservado"],
        "risks": ["Sensação de aprisionamento e queda de motivação", "Baixo envolvimento com a organização",
                  "Decisões de carreira adiadas por medo"],
        "next_steps": ["Liste o que exatamente você perderia ao sair e quanto disso é real",
                       "Invista em empregabilidade: formação, rede e portfólio",
                       "Procure dentro da organização algo que possa voltar a te motivar",
                       "Defina um prazo para reavaliar sua situação com calma, sem urgência"],
        "manager": ["Entenda a história da pessoa: o que já foi bom aqui e o que mudou",
                    "Ofereça desafios novos, mobilidade interna ou projetos com significado",
                    "Não use benefícios como única estratégia de retenção. Isso aprofunda a trincheira",
                    "Converse sobre desenvolvimento com foco no futuro dela, dentro ou fora daqui"],
    },
    "EM_TRANSITO": {
        "key": (0, 0, 0), "name": "Em Trânsito", "color": "#6B7A8F",
        "tagline": "Ainda sem raízes por aqui.",
        "summary": ("Nenhum dos três vínculos aparece forte em você neste momento. Isso pode significar que você "
                    "chegou há pouco tempo e ainda está construindo sua relação com a organização, que está em "
                    "um momento de reavaliação ou que sua ligação é mais com a profissão, com as pessoas ou com "
                    "um projeto do que com a organização em si. É um perfil de liberdade, mas também de baixa "
                    "ancoragem."),
        "strengths": ["Liberdade para decidir o próprio caminho", "Olhar externo e menos enviesado",
                      "Abertura para mudanças"],
        "risks": ["Saída repentina diante de uma oferta melhor", "Pouco senso de pertencimento",
                  "Distância em relação à equipe e à cultura"],
        "next_steps": ["Pergunte-se o que te faria querer construir uma história aqui",
                       "Aproxime-se de pessoas e projetos com os quais você se identifica",
                       "Converse com sua liderança sobre expectativas, de ambos os lados",
                       "Se estiver em reavaliação, faça-a com intenção e com dados"],
        "manager": ["Se a pessoa for nova, invista em integração, mentoria e vínculos com o time",
                    "Descubra o que motiva essa pessoa e conecte o trabalho a isso",
                    "Converse com transparência sobre perspectivas de carreira",
                    "Crie rituais de pertencimento no time"],
    },
}

PROFILE_BY_KEY = {tuple(p["key"]): code for code, p in PROFILES.items()}


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def to100(m):
    return round((m - 1) / 5 * 100, 1)


def classify(scores, cutoffs):
    high = cutoffs.get("high", 4.0)
    border = cutoffs.get("border", 0.35)
    key = tuple(1 if scores[b] >= high else 0 for b in ("CO", "CN", "EN"))
    borderline = [b for b in ("CO", "CN", "EN") if abs(scores[b] - high) < border]
    return PROFILE_BY_KEY[key], borderline


def score(instrument, answers):
    """answers = {"likert": {item_id: 1..6}, "rank": {elem_id: [bond1st, bond2nd, bond3rd]},
                  "presence": {elem_id: 1..4}}"""
    lik = answers.get("likert", {})
    by_bond, by_sub = {"CO": [], "CN": [], "EN": []}, {}
    for it in instrument["likert"]:
        v = lik.get(it["id"])
        if v is None:
            continue
        v = int(v)
        if it.get("reverse"):
            v = 7 - v
        by_bond[it["bond"]].append(v)
        by_sub.setdefault(it["bond"] + "|" + it["sub"], []).append(v)
    bonds = {b: round(_mean(v), 2) for b, v in by_bond.items()}
    subs = {k: round(_mean(v), 2) for k, v in by_sub.items()}
    profile, borderline = classify(bonds, instrument.get("cutoffs", {}))

    # Parte 2: via cultural de cada elemento
    ranks, pres = answers.get("rank", {}), answers.get("presence", {})
    elements = {}
    lvl_acc = {l: {"CO": 0.0, "CN": 0.0, "EN": 0.0, "w": 0.0, "p": []} for l in LEVELS}
    tot = {"CO": 0.0, "CN": 0.0, "EN": 0.0, "w": 0.0}
    for el in instrument["culture"]:
        order = ranks.get(el["id"])
        if not order or len(order) != 3:
            continue
        p = int(pres.get(el["id"], 2))
        pts = {order[0]: 2, order[1]: 1, order[2]: 0}
        elements[el["id"]] = {"via": order[0], "order": order, "presence": p, "level": el["level"], "name": el["name"]}
        acc = lvl_acc[el["level"]]
        for b in ("CO", "CN", "EN"):
            acc[b] += pts[b] * p
            tot[b] += pts[b] * p
        acc["w"] += 3 * p
        tot["w"] += 3 * p
        acc["p"].append(p)
    levels = {}
    for l, acc in lvl_acc.items():
        if acc["w"] == 0:
            continue
        share = {b: round(acc[b] / acc["w"] * 100, 1) for b in ("CO", "CN", "EN")}
        levels[l] = {"share": share, "intensity": round((_mean(acc["p"]) - 1) / 3 * 100, 1),
                     "via": max(share, key=share.get)}
    culture_share = ({b: round(tot[b] / tot["w"] * 100, 1) for b in ("CO", "CN", "EN")}
                     if tot["w"] else {"CO": 0, "CN": 0, "EN": 0})
    # Profundidade de interiorização (P2 da dissertação): peso do Comprometimento
    # nos pressupostos, o nível mais profundo da cultura.
    depth = levels.get("PRE", {}).get("share", {}).get("CO")
    return {
        "bonds": bonds, "bonds100": {b: to100(v) for b, v in bonds.items()}, "subs": subs,
        "profile": profile, "borderline": borderline,
        "elements": elements, "levels": levels, "culture_share": culture_share,
        "depth": depth, "cutoff": instrument.get("cutoffs", {}).get("high", 4.0),
    }


def culture_reading(result):
    """Texto interpretativo da leitura cultural a partir do vínculo."""
    out = []
    names = {b: BONDS[b]["name"] for b in BONDS}
    lv = result.get("levels", {})
    vias = {d["via"] for d in lv.values()}
    if len(lv) == 3 and len(vias) == 1:
        via = vias.pop()
        txt = {"CO": "pelo afeto: os três níveis, do visível ao mais profundo, geram identificação e orgulho",
               "CN": "pela obediência: dos artefatos aos pressupostos, a cultura funciona mais como padrão a seguir do que como algo que você abraça",
               "EN": "pela necessidade: em todos os níveis, a cultura reforça a sensação de que sair seria custoso"}[via]
        out.append(f"A cultura chega até você de forma coerente {txt}.")
        lv = {}
    for l in ("ART", "VAL", "PRE"):
        if l not in lv:
            continue
        d = lv[l]
        via = d["via"]
        inten = d["intensity"]
        force = "muito forte" if inten >= 75 else "forte" if inten >= 50 else "moderada" if inten >= 25 else "fraca"
        txt = {
            "CO": "chega até você pelo afeto. Aqui a cultura gera identificação e orgulho",
            "CN": "chega até você pela obediência. Aqui a cultura funciona mais como padrão a seguir do que como algo que você abraça",
            "EN": "chega até você pela necessidade. Aqui a cultura reforça a sensação de que sair seria custoso",
        }[via]
        out.append(f"No nível de {LEVELS[l]['name']}, de presença {force} para você, a cultura {txt}.")
    co = result["bonds"]["CO"]
    share = result.get("culture_share", {})
    high = result.get("cutoff", 4.0)
    if share:
        top = max(share, key=share.get)
        if co >= high and top != "CO":
            out.append("Seu comprometimento é alto, mas a cultura não é a principal fonte dele. "
                       "É provável que ele esteja ancorado em pessoas, no trabalho em si ou na sua trajetória, "
                       "mais do que nos elementos culturais da organização.")
        if co < high and top == "CO":
            out.append("Os elementos culturais te tocam pelo afeto, mas isso ainda não se converteu em "
                       "comprometimento com a organização como um todo. Vale olhar o que está no caminho: "
                       "liderança, condições de trabalho ou reconhecimento.")
        if top == "CN":
            out.append(f"No conjunto, {names['CN']} é a principal via pela qual a cultura chega até você, "
                       "o que, como mostra a pesquisa na PMSC, é típico de culturas com normas e hierarquia fortes.")
    if result.get("depth") is not None:
        d = result["depth"]
        if d >= 50:
            out.append("A cultura está interiorizada em você no nível mais profundo, o dos pressupostos. "
                       "Isso costuma sustentar vínculos afetivos duradouros.")
        elif d <= 20:
            out.append("No nível mais profundo, o dos pressupostos, sua relação com a cultura é mais crítica do que "
                       "afetiva. Você enxerga as \"verdades\" da organização com distância.")
    return out
