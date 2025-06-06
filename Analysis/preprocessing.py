from snappy import ProductIO, GPF, HashMap, ProgressMonitor

GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

def write_product(product, output_path):
    ProductIO.writeProduct(product, output_path, "GeoTIFF")


def process_sentinel2(input_path, output_path):
    product = ProductIO.readProduct(input_path)
    params = HashMap()
    params.put("targetResolution", 10.0)
    params.put("resamplingType", "BILINEAR")
    resampled = GPF.createProduct("Resample", params, product)
    write_product(resampled, output_path)


def process_sentinel1(input_path, output_path):
    product = ProductIO.readProduct(input_path)

    params_res = HashMap()
    params_res.put("targetResolution", 10.0)
    params_res.put("resamplingType", "BILINEAR")
    resampled = GPF.createProduct("Resample", params_res, product)

    tnr = GPF.createProduct("ThermalNoiseRemoval", HashMap(), resampled)

    bnr = GPF.createProduct("Remove-GRD-Border-Noise", HashMap(), tnr)

    params_tc = HashMap()
    params_tc.put("pixelSpacingInMeter", 10.0)
    tc = GPF.createProduct("Terrain-Correction", params_tc, bnr)

    params_cal = HashMap()
    params_cal.put("outputSigmaBand", True)
    cal = GPF.createProduct("Calibration", params_cal, tc)

    sigma_bands = [b for b in cal.getBandNames() if b.startswith("Sigma0")]
    params_db = HashMap()
    params_db.put("sourceBands", sigma_bands)
    target_db = [b + "_dB" for b in sigma_bands]
    params_db.put("targetBands", target_db)
    db = GPF.createProduct("LinearToFromdB", params_db, cal)

    write_product(db, output_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Использование:")
        print("  python preprocess.py <S2_input> <S1_input> <output_folder>")
        sys.exit(1)

    s2_input = sys.argv[1]
    s1_input = sys.argv[2]
    out_folder = sys.argv[3].rstrip("/")

    s2_out = f"{out_folder}/S2_resampled.tif"
    s1_out = f"{out_folder}/S1_preprocessed_dB.tif"

    process_sentinel2(s2_input, s2_out)
    process_sentinel1(s1_input, s1_out)

    print("Все операции успешно завершены.")