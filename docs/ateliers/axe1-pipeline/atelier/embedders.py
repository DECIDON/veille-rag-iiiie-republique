"""Étape 3 — encodage dense **et** sparse des granulats (leçon 0003).

Le modèle de référence est ``BAAI/bge-m3`` (MIT, 568 M) : il fournit d'une
part les vecteurs denses de 1 024 dimensions (sens, paraphrase), d'autre part
les vecteurs sparse appris (pondérations lexicales, façon BM25 appris) — la
veille retient précisément ce double usage, qui rend l'hybride possible sans
moteur lexical séparé, sur CPU.

Choix d'implémentation : ``sentence-transformers`` ne sait charger que la
partie **dense** de bge-m3 — sa classe de modèles sparse (``SparseEncoder``,
pour SPLADE & co) ignore la tête sparse du dépôt ``BAAI/bge-m3``, absente de
son ``modules.json`` (le nom ``SparseTextEmbeddingModel`` importé ici à
l'origine n'a jamais existé dans la bibliothèque). La tête sparse n'étant
qu'un ``Linear(1 024 → 1)`` livré avec les poids (``sparse_linear.pt``,
~ 4 Ko), on charge le modèle en direct via ``transformers`` et on applique
la formule officielle (implémentation de référence FlagEmbedding, BAAI) :

- poids par jeton : ``ReLU(Linear(h))`` — un scalaire par token ;
- jetons répétés : on garde le poids maximal par identifiant de jeton ;
- jetons spéciaux (cls/eos/pad/unk) exclus.

Côté dense, on reproduit exactement la configuration ``modules.json`` que
``sentence-transformers`` applique à ce modèle (pooling CLS, normalisation
L2), à un chargement unique des poids près au lieu de deux (2,3 Go en RAM
au lieu de 4,6).

Le second encodeur, ``DummyEmbedder``, n'a aucune valeur sémantique : sac de
mots déterministe (hash de tokens). Il sert uniquement à tester la plomberie
(cache, indexation, fusion) sans télécharger deux gigaoctets de poids, et aux
tests d'intégration. Ne jamais l'employer pour une mesure de qualité.
"""
from __future__ import annotations

import hashlib
import math
import re

_MOTS = re.compile(r"[0-9a-zà-ÿ]+")


class DummyEmbedder:
    """Emballeur lexical déterministe, hors-ligne, pour tests et smoke tests."""

    nom = "dummy"
    dim = 1024

    @staticmethod
    def _mots(texte: str) -> list[str]:
        return _MOTS.findall(texte.lower())

    @staticmethod
    def _hachage(mot: str) -> int:
        return int.from_bytes(
            hashlib.blake2b(mot.encode("utf-8"), digest_size=8).digest(), "big",
        )

    def encode_dense(self, textes: list[str]) -> list[list[float]]:
        vecteurs = []
        for texte in textes:
            v = [0.0] * self.dim
            for mot in self._mots(texte):
                h = self._hachage(mot)
                v[h % self.dim] += 1.0 if (h >> 63) else -1.0
            norme = math.sqrt(sum(c * c for c in v)) or 1.0
            vecteurs.append([c / norme for c in v])
        return vecteurs

    def encode_sparse(self, textes: list[str]) -> list[dict[int, float]]:
        vectors = []
        for texte in textes:
            v: dict[int, float] = {}
            for mot in self._mots(texte):
                indice = self._hachage(mot) % (2 ** 31)
                v[indice] = v.get(indice, 0.0) + 1.0
            vectors.append(v)
        return vectors


class BgeM3Embedder:
    """bge-m3 chargé en direct (transformers + torch) : dense + sparse appris.

    Dense : pooling CLS puis normalisation L2 — la configuration que
    ``sentence-transformers`` applique à ce modèle (voir ``modules.json`` du
    dépôt). Sparse : tête ``sparse_linear`` appliquée à la main, formule de
    la référence FlagEmbedding (voir docstring du module).
    """

    nom = "bge-m3"
    dim = 1024
    MODELE = "BAAI/bge-m3"
    TETE_SPARSE = "sparse_linear.pt"
    MAX_JETONS = 512  # les granulats font ≤ 1 200 caractères ; garde-fou mémoire

    def __init__(self, device: str | None = None) -> None:
        # Import différé : les tests unitaires n'ont ni torch ni le modèle.
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tokeniseur = AutoTokenizer.from_pretrained(self.MODELE)
        self._modele = AutoModel.from_pretrained(self.MODELE).to(self._device).eval()
        # Tête sparse : un simple Linear(1 024 → 1) dont les poids sont livrés
        # avec le modèle (c'est exactement ce que fait FlagEmbedding).
        tete = torch.nn.Linear(self._modele.config.hidden_size, 1)
        tete.load_state_dict(
            torch.load(hf_hub_download(self.MODELE, self.TETE_SPARSE), map_location="cpu"),
        )
        self._tete_sparse = tete.to(self._device).eval()
        # cls/eos/pad/unk écartés du sparse, comme dans la référence FlagEmbedding.
        self._speciaux = frozenset(
            id_
            for id_ in (
                getattr(self._tokeniseur, f"{champ}_token_id", None)
                for champ in ("cls", "eos", "pad", "unk")
            )
            if id_ is not None
        )

    def _passe(self, textes: list[str]):
        """Une passe du transformeur : états cachés, ids des jetons, poids lexicaux."""
        torch = self._torch
        encodage = self._tokeniseur(
            textes, padding=True, truncation=True,
            max_length=self.MAX_JETONS, return_tensors="pt",
        ).to(self._device)
        # no_grad (et non inference_mode) : les tensors retournés restent des
        # tensors normaux, utilisables par la tête sparse calculée hors du bloc.
        with torch.no_grad():
            etats = self._modele(**encodage).last_hidden_state
            # poids par jeton : ReLU(Linear(h)) — la formule de la référence ;
            # les positions de bourrage ont un id = pad, écarté au masquage.
            poids = torch.relu(self._tete_sparse(etats)).squeeze(-1)  # [lot, longueur]
        return etats, encodage["input_ids"], poids

    def encode_dense(self, textes: list[str], batch_size: int = 16) -> list[list[float]]:
        torch = self._torch
        vecteurs: list[list[float]] = []
        for debut in range(0, len(textes), batch_size):
            etats, _, _ = self._passe(list(textes)[debut:debut + batch_size])
            # pooling CLS (jeton 0) puis normalisation L2, comme la config ST
            denses = torch.nn.functional.normalize(etats[:, 0], p=2, dim=1)
            vecteurs.extend([[float(x) for x in ligne] for ligne in denses])
        return vecteurs

    def encode_sparse(self, textes: list[str], batch_size: int = 16) -> list[dict[int, float]]:
        # Max des poids par identifiant de jeton, construit à la main dans un
        # dict (algorithme de _process_token_weights, FlagEmbedding) : le
        # scatter_reduce « amax » de la référence est un no-op silencieux sur
        # certains builds de torch (constaté en 2.14.1+cu130), et le dict évite
        # un tensor dense de 250 002 dimensions par ligne.
        plonges: list[dict[int, float]] = []
        for debut in range(0, len(textes), batch_size):
            _, ids, poids = self._passe(list(textes)[debut:debut + batch_size])
            for ligne_ids, ligne_poids in zip(ids.tolist(), poids.tolist()):
                v: dict[int, float] = {}
                for indice, p in zip(ligne_ids, ligne_poids):
                    if indice in self._speciaux:
                        continue
                    if p > v.get(indice, 0.0):
                        v[indice] = p
                plonges.append(v)
        return plonges


def creer(nom: str, device: str | None = None):
    """Fabrique l'encodeur demandé (``bge-m3`` ou ``dummy``)."""
    if nom == "dummy":
        return DummyEmbedder()
    if nom == "bge-m3":
        return BgeM3Embedder(device=device)
    raise ValueError(f"encodeur inconnu : {nom!r} (attendu « bge-m3 » ou « dummy »)")
