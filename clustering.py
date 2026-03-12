"""
NLP-nameOrigins | Étape 1 : Regroupement des variantes de noms de famille
==========================================================================
Objectif :
    Regrouper les noms de famille qui partagent la même origine en clusters
    de variantes (ex: durand / durant / duran).

Algorithme :
    Union-Find : deux noms sont dans le même groupe s'ils partagent
    au moins un origin_id commun.

Entrées :
    data/names.json    → liste des noms avec leurs origin_ids
    data/origins.json  → dictionnaire origin_id → texte d'origine

Sortie :
    output/clusters.json → clusters de variantes avec leurs textes d'origine
"""

import json
from collections import defaultdict


# ── 1. Chargement des données ─────────────────────────────────────────────────

with open("data/names.json", "r", encoding="utf-8") as f:
    names_data = json.load(f)

with open("data/origins.json", "r", encoding="utf-8") as f:
    origins_data = json.load(f)

print(f" Chargement : {len(names_data)} noms, {len(origins_data)} origines")


# ── 2. Structure Union-Find ───────────────────────────────────────────────────

class UnionFind:
    """
    Structure de données pour regrouper des éléments en ensembles disjoints.
    Utilisée ici pour regrouper les noms qui partagent une même origine.
    """

    def __init__(self, items):
        self.parent = {x: x for x in items}
        self.rank   = {x: 0  for x in items}

    def find(self, x):
        """Trouve la racine du groupe de x (avec compression de chemin)."""
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # compression
            x = self.parent[x]
        return x

    def union(self, a, b):
        """Fusionne les groupes de a et b."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


# ── 3. Construction du graphe noms ↔ origines ─────────────────────────────────

all_names = [entry["name"] for entry in names_data]
uf = UnionFind(all_names)

# Regrouper les noms qui partagent un même origin_id
origin_to_names = defaultdict(list)
for entry in names_data:
    for oid in entry["origins"]:
        origin_to_names[oid].append(entry["name"])

for oid, group in origin_to_names.items():
    for i in range(1, len(group)):
        uf.union(group[0], group[i])


# ── 4. Construction des clusters ──────────────────────────────────────────────

name_to_origins = {entry["name"]: entry["origins"] for entry in names_data}
clusters = defaultdict(lambda: {"names": [], "origin_ids": set()})

for name in all_names:
    root = uf.find(name)
    clusters[root]["names"].append(name)
    for oid in name_to_origins[name]:
        clusters[root]["origin_ids"].add(oid)


# ── 5. Mise en forme du résultat ──────────────────────────────────────────────

output = []
for root, cluster in clusters.items():
    origin_ids   = sorted(cluster["origin_ids"])
    origin_texts = {oid: origins_data.get(oid, "") for oid in origin_ids}

    output.append({
        "representative": min(cluster["names"]),   # nom canonique (alphabétique)
        "variants":       sorted(cluster["names"]),
        "origin_ids":     origin_ids,
        "origin_texts":   origin_texts,
    })

output.sort(key=lambda x: x["representative"])


# ── 6. Sauvegarde ─────────────────────────────────────────────────────────────

with open("output/clusters.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)


# ── 7. Statistiques ───────────────────────────────────────────────────────────

sizes  = [len(c["variants"]) for c in output]
solo   = sum(1 for s in sizes if s == 1)
multi  = len(output) - solo

print(f"\n Résultats :")
print(f"   Clusters total          : {len(output)}")
print(f"   Noms isolés             : {solo}")
print(f"   Groupes de variantes    : {multi}")
print(f"   Taille max d'un groupe  : {max(sizes)}")
print(f"   Taille moyenne          : {sum(sizes)/len(sizes):.2f}")

print(f"\n Exemples de groupes trouvés :")
exemples = sorted([c for c in output if len(c["variants"]) > 1],
                  key=lambda x: len(x["variants"]), reverse=True)[:5]
for c in exemples:
    print(f"   {c['variants']}")

print(f"\n Résultat sauvegardé dans output/clusters.json")