import sys
import rasterio
from rasterio.mask import mask
import fiona

def clip_image(image_path, kml_path, output_path):
    with fiona.open(kml_path, driver='KML') as kml:
        geometries = [feat["geometry"] for feat in kml]
    with rasterio.open(image_path) as src:
        out_image, out_transform = mask(src, geometries, crop=True)
        out_meta = src.meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(out_image)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Использование: python clip.py <input_image> <input_kml> <output_image>")
        sys.exit(1)
    image_path = sys.argv[1]
    kml_path = sys.argv[2]
    output_path = sys.argv[3]
    clip_image(image_path, kml_path, output_path)