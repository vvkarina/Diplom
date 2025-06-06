#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve.py v2
-----------

KServe-сервер:
    • /parser   → экспорт S2/S1 (+cloud) по KML
    • /cropper  → гео-кроп GeoTIFF под KML-контур
    • /clouds   → CR-Net (S2+S1) inference

© 2025
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import ee
import kserve
import numpy as np
import rasterio
import torch
import xml.etree.ElementTree as ET
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.windows import Window
from shapely.geometry import Polygon, mapping
from shapely.ops import transform as shp_transform
from pyproj import Transformer

from export_roi_batch import export_roi_batch

from config import CONFIG
from models.model_CR_net import ModelCRNet
from train_test.dataloader import AlignedDataset


# ─── EE init ───────────────────────────────────────────────────────────────
ee.Initialize(opt_url="https://earthengine-highvolume.googleapis.com")


# ─── LOGGING ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("serve")


# ───────────────────────────── 1. PARSER ───────────────────────────────────


class ParserPipeline(kserve.Model):
    def __init__(self):
        super().__init__("parser")
        self.ready = True

    def load(self) -> bool:
        return True

    def predict(
        self, request: kserve.InferRequest, headers=None
    ) -> Dict:
        try:
            raw = request.inputs[0].data[0]
            payload = (
                raw
                if isinstance(raw, dict)
                else json.loads(raw)
            )

            kml_path = Path(payload["kml"])
            out_dir = Path(payload.get("out_dir", "./downloads"))
            out_dir.mkdir(parents=True, exist_ok=True)

            export_roi_batch(
                kml=kml_path,
                date=payload.get("date"),
                start=payload.get("start"),
                end=payload.get("end"),
                out_dir=out_dir,
                scale=int(payload.get("scale", 10)),
            )

            files = sorted(str(p) for p in out_dir.glob("*.tif"))

            return {
                "model_name": self.name,
                "id": "parser-ok",
                "outputs": [
                    {
                        "name": "downloaded_files",
                        "datatype": "STRING",
                        "shape": [len(files)],
                        "data": files,
                    }
                ],
            }

        except Exception as exc:
            logger.exception("Parser failed")
            return {
                "model_name": self.name,
                "id": "parser-error",
                "outputs": [
                    {
                        "name": "message",
                        "datatype": "BYTES",
                        "shape": [1],
                        "data": [str(exc).encode()],
                    }
                ],
            }


# ───────────────────────────── 2. CROPPER ──────────────────────────────────


def _reply_error(model_name: str, msg: str) -> Dict:
    return {
        "model_name": model_name,
        "id": f"{model_name}-error",
        "outputs": [
            {
                "name": "message",
                "datatype": "BYTES",
                "shape": [1],
                "data": [msg.encode()],
            }
        ],
    }


class CropperPipeline(kserve.Model):
    def __init__(self):
        super().__init__("cropper")
        self.ready = True

    def load(self) -> bool:
        return True

    def predict(
        self, request: kserve.InferRequest, headers=None
    ) -> Dict:
        try:
            raw = request.inputs[0].data[0]
            payload = (
                raw
                if isinstance(raw, dict)
                else json.loads(raw)
            )

            raster_path = Path(payload["raster"])
            kml_path = Path(payload["kml"])
            out_dir = Path(payload.get("out_dir", raster_path.parent))

            out_path = export_roi_batch(raster_path, kml_path, out_dir)

            return {
                "model_name": self.name,
                "id": "cropper-ok",
                "outputs": [
                    {
                        "name": "cropped_tif",
                        "datatype": "STRING",
                        "shape": [1],
                        "data": [str(out_path)],
                    }
                ],
            }

        except Exception as exc:
            logger.exception("Cropper failed")
            return _reply_error(self.name, str(exc))


# ───────────────────────── 3. CLOUD-REMOVAL ────────────────────────────────


_normalizer = AlignedDataset(cfg={}, filelist=[])


def _normalize_opt(a: np.ndarray) -> np.ndarray:
    return _normalizer.get_normalized_data(
        a.astype(np.float32), data_type=2
    )


def _normalize_sar(a: np.ndarray) -> np.ndarray:
    return _normalizer.get_normalized_data(
        a.astype(np.float32), data_type=1
    )


class CloudRemovalPipeline(kserve.Model):
    def __init__(self):
        super().__init__("clouds")

        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        self.model_cr = ModelCRNet(CONFIG)
        self.ready = False

    def load(self) -> bool:
        ckpt_path = Path(CONFIG.get("test_ckpt", ""))
        if not ckpt_path.exists():
            logger.error(f"Checkpoint not found: {ckpt_path}")
            return False

        state = torch.load(ckpt_path, map_location=self.device)
        self.model_cr.net_G.load_state_dict(state["network"])
        self.model_cr.net_G.eval().to(self.device)
        self.ready = True
        logger.info(
            f"CR-Net loaded ({ckpt_path}) | device={self.device}"
        )
        return True

    @torch.no_grad()
    def predict(
        self, request: kserve.InferRequest, headers=None
    ) -> Dict:
        if not self.ready:
            return _reply_error(self.name, "Model not ready")

        try:
            raw = request.inputs[0].data[0]
            payload = (
                raw
                if isinstance(raw, dict)
                else json.loads(raw)
            )

            pairs: List[Dict] = payload.get("pairs", [])
            save_root = (
                Path(payload.get("save_dir", ""))
                if payload.get("save_dir")
                else None
            )

            if save_root:
                save_root.mkdir(parents=True, exist_ok=True)

            results: List[str] = []
            for p in pairs:
                opt_path = Path(p["optical"])
                sar_path = Path(p["sar"])
                results.append(
                    str(
                        self._run_pair(opt_path, sar_path, save_root)
                    )
                )

            return {
                "model_name": self.name,
                "id": "clouds-ok",
                "outputs": [
                    {
                        "name": "prediction_paths",
                        "datatype": "STRING",
                        "shape": [len(results)],
                        "data": results,
                    }
                ],
            }

        except Exception as exc:
            logger.exception("Inference failed")
            return _reply_error(self.name, str(exc))

    @torch.no_grad()
    def _run_pair(
        self,
        opt_path: Path,
        sar_path: Path,
        save_root: Optional[Path],
    ) -> Path:
        with rasterio.open(opt_path) as src_o:
            opt = _normalize_opt(src_o.read(range(1, 14)))
            transform = src_o.transform
            crs = src_o.crs

        with rasterio.open(sar_path) as src_s:
            sar = _normalize_sar(src_s.read())

        opt_t = torch.from_numpy(opt).unsqueeze(0).to(self.device)
        sar_t = torch.from_numpy(sar).unsqueeze(0).to(self.device)

        pred_np = (
            self.model_cr.net_G(opt_t, sar_t)
            .squeeze(0)
            .cpu()
            .numpy()
        )
        out_path = (
            save_root
            or opt_path.parent
        ) / f"{opt_path.stem}_pred.tiff"

        c, h, w = pred_np.shape

        with rasterio.open(
            out_path,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=c,
            dtype="float32",
            crs=crs,
            transform=transform,
        ) as dst:
            for b in range(c):
                dst.write(pred_np[b], b + 1)

        return out_path


# ───────────────────────────── 4. START ────────────────────────────────────


if __name__ == "__main__":
    models = [
        ParserPipeline(),
        CropperPipeline(),
        CloudRemovalPipeline(),
    ]

    # preload CR-Net
    if not models[-1].load():
        raise RuntimeError("CR-Net failed to load")

    kserve.ModelServer(
        http_port=8100, enable_docs_url=True
    ).start(models=models)