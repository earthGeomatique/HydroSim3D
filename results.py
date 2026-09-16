"""Modele de resultats commun aux moteurs SWMM et HEC-RAS.

Les deux moteurs produisent des sorties tres differentes (series temporelles
sur un graphe pour SWMM, maillage 2D pour HEC-RAS). :class:`SimulationResult`
est le format pivot que consomme le panneau 3D, independant du moteur
d'origine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np


@dataclass
class SimulationResult:
    engine: str
    times: List[datetime]

    #: coordonnees des noeuds / cellules, tableau (N, 3) -> x, y, z (fond)
    points: np.ndarray

    #: grandeurs scalaires par pas de temps : nom -> tableau (T, N)
    scalars: Dict[str, np.ndarray] = field(default_factory=dict)

    #: vecteurs d'ecoulement par pas de temps : (T, N, 3), optionnel
    vectors: Optional[np.ndarray] = None

    #: connectivite du maillage (liste d'aretes ou de faces), optionnel.
    #: Pour SWMM : liste de tuples (index_amont, index_aval) = conduites.
    #: Pour HEC-RAS : liste de faces de cellules du maillage 2D.
    topology: Optional[List] = None

    #: metadonnees libres (nom du fichier source, unites, etc.)
    metadata: Dict = field(default_factory=dict)

    @property
    def n_steps(self) -> int:
        return len(self.times)

    @property
    def n_points(self) -> int:
        return int(self.points.shape[0]) if self.points is not None else 0

    def scalar_at(self, name: str, step: int) -> np.ndarray:
        return self.scalars[name][step]

    def vector_at(self, step: int) -> Optional[np.ndarray]:
        if self.vectors is None:
            return None
        return self.vectors[step]

    def available_scalars(self) -> List[str]:
        return sorted(self.scalars.keys())
