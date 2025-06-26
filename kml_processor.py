import geopandas as gpd
import pandas as pd
import re
from fiona import listlayers
import os

output_dir = 'outputs'
os.makedirs(output_dir, exist_ok=True)

def parse_desc(desc):
    if pd.isnull(desc):
        return {}
    pairs = re.findall(r'([^:<>\n]+):\s*([^<>\n]+)', desc)
    return {k.strip(): v.strip() for k, v in pairs}

def replace_or_append(pattern, value, desc):
    if re.search(pattern, desc):
        return re.sub(pattern, value, desc)
    elif value:
        return (desc + ('\n' if desc and not desc.endswith('\n') else '') + value).strip()
    return desc

def get_tipo_cliente(desc):
    if pd.isnull(desc):
        return None
    match = re.search(r'Tipo de cliente:\s*([^\n<]+)', desc)
    return match.group(1).strip() if match else None

def update_description(row):
    desc_point = row['Description_point'] or ''
    desc_poly = row['Description_polygon']
    desc_poly_str = str(desc_poly) if pd.notnull(desc_poly) else ''
    cod_transporte = re.search(r'Cod\. Transporte:\s*([^\n<]+)', desc_poly_str)
    transporte = re.search(r'Transporte:\s*([^\n<]+)', desc_poly_str)
    frecuencia = re.search(r'Frecuencia:\s*([^\n<]+)', desc_poly_str)
    desc = desc_point
    if cod_transporte:
        desc = replace_or_append(r'Cod\. Transporte:\s*[^\n<]+', f'Cod. Transporte: {cod_transporte.group(1).strip()}', desc)
    if transporte:
        desc = replace_or_append(r'Transporte:\s*[^\n<]+', f'Transporte: {transporte.group(1).strip()}', desc)
    if frecuencia:
        desc = replace_or_append(r'Frecuencia:\s*[^\n<]+', f'Frecuencia: {frecuencia.group(1).strip()}', desc)
    return desc.strip()

def process_kml(kml_file):
    columnas_requeridas = [
        'Código', 'Local', 'Calle', 'Población', 'Tipo de cliente',
        'Cod. Transporte', 'Transporte', 'Frecuencia',
        'Kilos Promedio Semanal', 'Latitud', 'Longitud'
    ]
    tipos_clientes = {
        'supermercados': 'Supermercados',
        'foodservice': 'Foodservice',
        'tradicional': 'Tradicional',
        'industriales': 'Industriales'
    }
    columns_to_save = ['Name', 'Description', 'geometry']
    max_elements = 2000
    csv_chunks = []

    layers = listlayers(kml_file)
    gdfs = [gpd.read_file(kml_file, driver='KML', layer=layer) for layer in layers]
    mapf_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:4326")

    map_polygons = mapf_gdf[mapf_gdf.geometry.type == 'Polygon']
    map_points = mapf_gdf[mapf_gdf.geometry.type == 'Point']

    map_points['tipo_cliente'] = map_points['Description'].apply(get_tipo_cliente)

    for tipo_key, tipo_val in tipos_clientes.items():
        mapa_tipo = map_points[map_points['tipo_cliente'] == tipo_val].reset_index(drop=True)
        if mapa_tipo.empty:
            continue
        joined = gpd.sjoin(
            mapa_tipo,
            map_polygons[['Name', 'Description', 'geometry']],
            how='left',
            predicate='within',
            lsuffix='point',
            rsuffix='polygon'
        )
        joined['Description'] = joined.apply(update_description, axis=1)
        joined['Name'] = joined['Name_polygon']
        total = len(joined)

        for i in range(0, total, max_elements):
            chunk = joined.iloc[i:i+max_elements]
            kml_output_path = os.path.join(output_dir,
                f'puntos_{tipo_key}_con_nombre_de_poligono_{i//max_elements + 1}.kml')
            chunk[columns_to_save].to_file(kml_output_path, driver='KML')
            chunk_csv = chunk[columns_to_save].copy()
            desc_df = chunk_csv['Description'].apply(parse_desc).apply(pd.Series)

            for col in columnas_requeridas:
                if col not in desc_df.columns:
                    desc_df[col] = None
            final_csv = pd.concat([chunk_csv[['Name']], desc_df[columnas_requeridas]], axis=1)
            csv_chunks.append(final_csv)

    if csv_chunks:
        all_points_df = pd.concat(csv_chunks, ignore_index=True)
        csv_output_path = os.path.join(output_dir, 'ClientesActualizados.csv')
        all_points_df.to_csv(csv_output_path, index=False)

    polygon_output_path = os.path.join(output_dir, 'poligonos.kml')
    map_polygons[['Name', 'Description', 'geometry']].to_file(polygon_output_path, driver='KML')