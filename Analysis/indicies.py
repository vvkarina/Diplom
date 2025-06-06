import sys
import numpy as np
import rasterio
import matplotlib.pyplot as plt

def get_index(name: str, B: np.ndarray) -> np.ndarray:
    eps = 1e-8
    if name == "NDWI":   return (B[2] - B[7]) / (B[2] + B[7] + eps)
    if name == "NDMI":   return (B[7] - B[11]) / (B[7] + B[11] + eps)
    if name == "NDVI":   return (B[7] - B[3]) / (B[7] + B[3] + eps)
    if name == "SR":     return B[7] / (B[3] + eps)
    if name == "REP":
        num = ((B[6] + B[3]) / 2) - B[4]
        den = (B[5] - B[4]) + eps
        return 700 + 40 * (num / den)
    if name == "EVI":    return 2.5 * (B[7] - B[3]) / (B[7] + 6 * B[3] - 7.5 * B[1] + 1 + eps)
    if name == "EVI2":   return 2.5 * (B[7] - B[3]) / (B[7] + B[3] + 1 + eps)
    if name == "ARVI":   return (B[7] - (2 * B[3] - B[1])) / (B[7] + (2 * B[3] - B[1]) + eps)
    if name == "SAVI":   return 1.5 * (B[7] - B[3]) / (B[7] + B[3] + 0.5 + eps)
    if name == "GOSAVI": return (B[7] - B[2]) / (B[7] + B[2] + 0.16 + eps)
    if name == "GARI":   return (B[7] - (B[2] - (B[1] - B[3]))) / (B[7] + (B[2] - (B[1] - B[3])) + eps)
    if name == "VARI":   return (B[2] - B[3]) / (B[2] + B[3] - B[1] + eps)
    raise ValueError(f"Unsupported index {name}")

INDEX_RANGES = {
    "NDWI":   (-1,  1),
    "NDMI":   (-1,  1),
    "NDVI":   (-1,  1),
    "SR":     ( 0, 10),
    "REP":  (680,750),
    "EVI":   (-1,  3),
    "EVI2":  (-1,  3),
    "ARVI":  (-2,  2),
    "SAVI":  (-1,  1),
    "GOSAVI":(-1,  1),
    "GARI":  (-2,  2),
    "VARI":  (-2,  2),
}

def main():
    if len(sys.argv) != 2:
        print("Использование: python compute_indices.py <путь_к_файлу.tif>")
        sys.exit(1)

    tif_path = sys.argv[1]

    with rasterio.open(tif_path) as src:
        B = src.read().astype('float32')
        nodata = src.nodata
        if nodata is not None:
            B = np.where(B == nodata, np.nan, B)

    for name, (low, high) in INDEX_RANGES.items():
        try:
            idx = get_index(name, B)
        except Exception as e:
            print(f"{name}: ошибка при вычислении → {e}")
            continue

        idx_min = np.nanmin(idx)
        idx_max = np.nanmax(idx)

        if idx_min >= low and idx_max <= high:
            print(f"{name}: OK ({idx_min:.3f}…{idx_max:.3f} ∈ [{low},{high}])")
        else:
            print(f"{name}: ВНЕ ДИАПАЗОНА ({idx_min:.3f}…{idx_max:.3f} ∉ [{low},{high}])")

        plt.figure(figsize=(8, 6))
        plt.imshow(idx, cmap='viridis')
        plt.colorbar(label=f"{name} value")
        plt.title(f"Тепловая карта {name}")
        output_png = f"{name}_heatmap.png"
        plt.savefig(output_png, bbox_inches='tight', dpi=300)
        plt.close()
        print(f"Сохранено: {output_png}")

if __name__ == "__main__":
    main()