"""Moteur SWMM : export .inp -> execution -> lecture des resultats."""
from __future__ import annotations

import os
import subprocess

from .base import LogCallback, ProgressCallback, SimulationEngine
from ..io.swmm_reader import read_swmm_output
from ..io.swmm_writer import write_swmm_inp
from ..results import SimulationResult


class SwmmEngine(SimulationEngine):
    name = "swmm"

    def __init__(self, config, layer_resolver):
        super().__init__(config, layer_resolver)
        self._node_index = None

    def export_inputs(self, working_dir: str, log_cb: LogCallback) -> str:
        inp_path = os.path.join(working_dir, "model.inp")
        self._node_index = write_swmm_inp(
            inp_path, self.config.network, self.config.simulation, self.resolve_layer
        )
        log_cb(f"Fichier SWMM ecrit : {inp_path} "
               f"({len(self._node_index['nodes'])} noeuds, {len(self._node_index['links'])} conduites)")
        return inp_path

    def run(self, input_path: str, working_dir: str,
            progress_cb: ProgressCallback, log_cb: LogCallback) -> str:
        rpt_path = os.path.join(working_dir, "model.rpt")
        out_path = os.path.join(working_dir, "model.out")

        try:
            self._run_via_pyswmm(input_path, rpt_path, out_path, progress_cb, log_cb)
        except ImportError:
            log_cb("pyswmm indisponible, tentative via l'executable swmm5 configure...")
            self._run_via_executable(input_path, rpt_path, out_path, log_cb)

        return out_path

    def _run_via_pyswmm(self, inp_path, rpt_path, out_path, progress_cb, log_cb):
        from pyswmm import Simulation

        with Simulation(inp_path, rpt_path, out_path) as sim:
            total_seconds = (sim.end_time - sim.start_time).total_seconds() or 1
            for step in sim:
                elapsed = (sim.current_time - sim.start_time).total_seconds()
                pct = 30 + int(55 * min(1.0, elapsed / total_seconds))
                progress_cb(pct, f"SWMM en cours... {sim.current_time}")
            log_cb("Simulation SWMM terminee (pyswmm).")

    def _run_via_executable(self, inp_path, rpt_path, out_path, log_cb):
        exe = self.config.simulation.executable_path
        if not exe or not os.path.isfile(exe):
            raise RuntimeError(
                "Ni 'pyswmm' ni un executable SWMM5 valide n'ont ete trouves. "
                "Installez pyswmm (pip install pyswmm) ou configurez le chemin "
                "de l'executable swmm5 dans l'onglet Simulation."
            )
        cmd = [exe, inp_path, rpt_path, out_path]
        log_cb(f"Execution : {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log_cb(proc.stdout or "")
        if proc.returncode != 0:
            raise RuntimeError(f"swmm5 a echoue (code {proc.returncode}) :\n{proc.stderr}")

    def import_results(self, output_path: str, log_cb: LogCallback) -> SimulationResult:
        result = read_swmm_output(output_path, self._node_index)
        log_cb(f"Resultats charges : {result.n_points} noeuds, {result.n_steps} pas de temps.")
        return result
